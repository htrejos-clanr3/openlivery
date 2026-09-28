import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import cast, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session, aliased, joinedload, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..models import Agent, CannedReply, Conversation, Message, User, now_utc
from ..schemas import (
    CannedReplyCreate,
    CannedReplyOut,
    CannedReplyUpdate,
    ConversationAssign,
    ConversationCreate,
    ConversationDetail,
    ConversationInboxOut,
    ConversationLabelsUpdate,
    ConversationModeUpdate,
    ConversationOut,
    SendMessageRequest,
)
from ..services.inbox_desk import (
    CONVERSATION_LABELS,
    MAX_CANNED,
    agency_member,
    allocate_shortcode,
    normalize_shortcode,
    sanitize_labels,
    seed_default_canned,
)
from ..services.tools import run_completion
from ..services.knowledge import build_system_prompt, retrieve_knowledge
from ..services.media import describe_image, transcribe_audio
from ..services.prompt_security import build_vision_instruction, to_llm_message
from ..services.providers import resolve_agent_credentials, resolve_provider_credentials
from ..services.usage import record_usage
from ..services.whatsapp import send_channel_message


router = APIRouter(prefix="/conversations", tags=["Conversations"])

MAX_MEDIA_BYTES = 20 * 1024 * 1024


def _conversation(db: Session, user: User, conversation_id: uuid.UUID) -> Conversation:
    conversation = db.scalar(
        select(Conversation)
        .options(
            selectinload(Conversation.messages),
            joinedload(Conversation.agent).joinedload(Agent.client),
            joinedload(Conversation.assigned_user),
        )
        .execution_options(populate_existing=True)
        .where(Conversation.id == conversation_id, Conversation.agency_id == user.agency_id)
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def _canned(db: Session, user: User, canned_id: uuid.UUID) -> CannedReply:
    reply = db.scalar(select(CannedReply).where(CannedReply.id == canned_id, CannedReply.agency_id == user.agency_id))
    if not reply:
        raise HTTPException(status_code=404, detail="Canned reply not found")
    return reply


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    agent_id: uuid.UUID | None = None,
    client_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = (
        select(Conversation)
        .options(joinedload(Conversation.assigned_user))
        .where(Conversation.agency_id == user.agency_id)
    )
    if agent_id:
        query = query.where(Conversation.agent_id == agent_id)
    if client_id:
        query = query.where(Conversation.client_id == client_id)
    return db.scalars(query.order_by(Conversation.updated_at.desc())).unique().all()


@router.get("/inbox", response_model=list[ConversationInboxOut])
def inbox(
    agent_id: uuid.UUID | None = None,
    channel: str | None = None,
    mode: str | None = None,
    assigned: str | None = None,
    label: str | None = None,
    search: str | None = None,
    unread: bool = False,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Latest message per conversation, resolved in SQL so we never load full
    # message histories just to build the list.
    ranked = select(
        Message.conversation_id.label("cid"),
        Message.content.label("content"),
        Message.sender_type.label("sender_type"),
        Message.created_at.label("created_at"),
        func.row_number().over(partition_by=Message.conversation_id, order_by=Message.created_at.desc()).label("rn"),
    ).subquery()
    last = select(ranked).where(ranked.c.rn == 1).subquery()
    unread_counts = (
        select(Message.conversation_id.label("cid"), func.count(Message.id).label("n"))
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Message.sender_type == "visitor",
            or_(Conversation.operator_read_at.is_(None), Message.created_at > Conversation.operator_read_at),
        )
        .group_by(Message.conversation_id)
    ).subquery()
    unread_count = func.coalesce(unread_counts.c.n, 0)
    assignee = aliased(User)

    query = (
        select(Conversation, Agent.name, last.c.content, unread_count.label("unread_count"), assignee.name)
        .join(Agent, Agent.id == Conversation.agent_id)
        .outerjoin(last, last.c.cid == Conversation.id)
        .outerjoin(unread_counts, unread_counts.c.cid == Conversation.id)
        .outerjoin(assignee, assignee.id == Conversation.assigned_user_id)
        .where(Conversation.agency_id == user.agency_id)
    )
    if agent_id:
        query = query.where(Conversation.agent_id == agent_id)
    if channel:
        query = query.where(Conversation.channel == channel)
    if mode in ("ai", "human"):
        query = query.where(Conversation.mode == mode)
    if assigned == "me":
        query = query.where(Conversation.assigned_user_id == user.id)
    elif assigned == "unassigned":
        query = query.where(Conversation.assigned_user_id.is_(None))
    if label in CONVERSATION_LABELS:
        query = query.where(cast(Conversation.labels, JSONB).contains([label]))
    if unread:
        query = query.where(unread_count > 0)
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Conversation.title).like(term),
                func.lower(func.coalesce(Conversation.contact_name, "")).like(term),
                func.lower(func.coalesce(last.c.content, "")).like(term),
            )
        )
    rows = db.execute(query.order_by(Conversation.updated_at.desc()).limit(limit).offset(offset)).all()
    return [
        {
            "id": conv.id,
            "agent_id": conv.agent_id,
            "agent_name": agent_name or "",
            "client_id": conv.client_id,
            "title": conv.title,
            "contact_name": conv.contact_name,
            "channel": conv.channel,
            "mode": conv.mode,
            "assigned_user_id": conv.assigned_user_id,
            "assigned_user_name": assignee_name,
            "labels": conv.labels or [],
            "preview": (content or "")[:140].strip(),
            "unread": int(row_unread_count) > 0,
            "unread_count": int(row_unread_count),
            "updated_at": conv.updated_at,
        }
        for conv, agent_name, content, row_unread_count, assignee_name in rows
    ]


@router.get("/canned", response_model=list[CannedReplyOut])
def list_canned(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    seed_default_canned(db, user.agency_id)
    db.commit()
    return db.scalars(
        select(CannedReply).where(CannedReply.agency_id == user.agency_id).order_by(CannedReply.shortcode)
    ).all()


@router.post("/canned", response_model=CannedReplyOut, status_code=status.HTTP_201_CREATED)
def create_canned(payload: CannedReplyCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    count = db.scalar(select(func.count()).select_from(CannedReply).where(CannedReply.agency_id == user.agency_id)) or 0
    if count >= MAX_CANNED:
        raise HTTPException(status_code=400, detail="You already have the maximum number of canned replies")
    explicit = bool(payload.shortcode and payload.shortcode.strip())
    shortcode = normalize_shortcode(payload.shortcode, payload.title)
    if explicit:
        taken = db.scalar(
            select(CannedReply.id).where(CannedReply.agency_id == user.agency_id, CannedReply.shortcode == shortcode)
        )
        if taken:
            raise HTTPException(status_code=409, detail="That shortcut is already in use")
    else:
        shortcode = allocate_shortcode(db, user.agency_id, shortcode)
    reply = CannedReply(
        agency_id=user.agency_id,
        shortcode=shortcode,
        title=payload.title.strip(),
        body=payload.body.strip(),
    )
    db.add(reply)
    db.commit()
    db.refresh(reply)
    return reply


@router.patch("/canned/{canned_id}", response_model=CannedReplyOut)
def update_canned(
    canned_id: uuid.UUID,
    payload: CannedReplyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reply = _canned(db, user, canned_id)
    values = payload.model_dump(exclude_unset=True)
    if "title" in values and values["title"] is not None:
        reply.title = values["title"].strip()
    if "body" in values and values["body"] is not None:
        reply.body = values["body"].strip()
    if "shortcode" in values:
        explicit = bool(values["shortcode"] and str(values["shortcode"]).strip())
        shortcode = normalize_shortcode(values["shortcode"], reply.title)
        if explicit:
            taken = db.scalar(
                select(CannedReply.id).where(
                    CannedReply.agency_id == user.agency_id,
                    CannedReply.shortcode == shortcode,
                    CannedReply.id != reply.id,
                )
            )
            if taken:
                raise HTTPException(status_code=409, detail="That shortcut is already in use")
            reply.shortcode = shortcode
        else:
            reply.shortcode = allocate_shortcode(db, user.agency_id, shortcode, exclude_id=reply.id)
    reply.updated_at = now_utc()
    db.commit()
    db.refresh(reply)
    return reply


@router.delete("/canned/{canned_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_canned(canned_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    reply = _canned(db, user, canned_id)
    db.delete(reply)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", response_model=ConversationDetail, status_code=status.HTTP_201_CREATED)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    agent = db.scalar(select(Agent).where(Agent.id == payload.agent_id, Agent.agency_id == user.agency_id))
    if not agent:
        raise HTTPException(status_code=400, detail="The selected agent does not exist")
    conversation = Conversation(
        agency_id=user.agency_id,
        client_id=agent.client_id,
        agent_id=agent.id,
    )
    db.add(conversation)
    db.commit()
    return _conversation(db, user, conversation.id)


@router.post("/{conversation_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(conversation_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conversation = _conversation(db, user, conversation_id)
    conversation.operator_read_at = now_utc()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _conversation(db, user, conversation_id)


def _ready_agent(db: Session, conversation: Conversation) -> tuple[Agent, tuple[str, str]]:
    """Validate the conversation can produce an AI reply and return the agent + credentials."""
    agent = conversation.agent
    if not agent.is_active:
        raise HTTPException(status_code=400, detail="This agent is inactive")
    credentials = resolve_agent_credentials(db, agent)
    if not credentials or not agent.model.strip():
        raise HTTPException(
            status_code=400,
            detail="This agent is not ready: set its model and add the provider API key in Settings.",
        )
    if conversation.mode == "human":
        raise HTTPException(status_code=409, detail="This conversation is being handled by a person")
    return agent, credentials


async def _generate_reply(
    db: Session,
    user: User,
    conversation: Conversation,
    agent: Agent,
    credentials: tuple[str, str],
    query: str,
) -> Conversation:
    """Run the agent over the current conversation and store the assistant reply."""
    knowledge = await retrieve_knowledge(db, agent, query)
    refreshed = _conversation(db, user, conversation.id)
    recent = refreshed.messages[-agent.memory_limit:] if agent.memory_limit else []
    history = [{"role": item.role, "content": item.content} for item in recent]
    messages = [
        {"role": "system", "content": build_system_prompt(agent, knowledge.text)},
        *[to_llm_message(item["role"], item["content"]) for item in history],
    ]
    base_url, api_key = credentials
    completion = await run_completion(
        db, agent, base_url, api_key, messages, temperature=agent.temperature, max_tokens=agent.max_tokens
    )
    db.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=completion.text,
            sources=knowledge.sources,
            tool_calls=completion.tool_calls,
            sender_type="ai",
            sender_name=agent.name,
        )
    )
    record_usage(db, agent.agency_id, agent.id, agent.provider, agent.model.strip(), completion)
    conversation.updated_at = now_utc()
    db.commit()
    return _conversation(db, user, conversation.id)


@router.post("/{conversation_id}/messages", response_model=ConversationDetail)
async def send_message(
    conversation_id: uuid.UUID,
    payload: SendMessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conversation = _conversation(db, user, conversation_id)
    agent, credentials = _ready_agent(db, conversation)

    content = payload.content.strip()
    if not conversation.messages:
        conversation.title = content[:80]
    conversation.updated_at = now_utc()
    db.add(Message(conversation_id=conversation.id, role="user", content=content, sender_type="visitor", sender_name="You"))
    db.commit()
    return await _generate_reply(db, user, conversation, agent, credentials, content)


@router.post("/{conversation_id}/media", response_model=ConversationDetail)
async def send_media_message(
    conversation_id: uuid.UUID,
    file: UploadFile = File(...),
    caption: str = Form(default=""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conversation = _conversation(db, user, conversation_id)
    agent, credentials = _ready_agent(db, conversation)

    content_type = (file.content_type or "").lower()
    is_image = content_type.startswith("image/")
    is_audio = content_type.startswith("audio/") or content_type.startswith("video/ogg")
    if not is_image and not is_audio:
        raise HTTPException(status_code=400, detail="Only image or audio files are supported")
    if is_image and not agent.image_enabled:
        raise HTTPException(status_code=400, detail="Image recognition is disabled for this agent")
    if is_audio and not agent.audio_enabled:
        raise HTTPException(status_code=400, detail="Audio recognition is disabled for this agent")

    # Transcription and vision run on the agency's OpenAI key.
    media_credentials = resolve_provider_credentials(db, agent.agency_id, "openai")
    if not media_credentials:
        raise HTTPException(status_code=400, detail="Add an OpenAI API key in Settings to process media")

    data = await file.read(MAX_MEDIA_BYTES + 1)
    if len(data) > MAX_MEDIA_BYTES:
        raise HTTPException(status_code=413, detail="The file is too large (20 MB max)")
    base_url, api_key = media_credentials
    caption = caption.strip()

    if is_image:
        model = agent.image_model.strip() or agent.model.strip()
        instruction = build_vision_instruction(
            "Describe con detalle el contenido de esta imagen para que un asistente pueda responder al usuario.",
            caption or None,
        )
        description = await describe_image(base_url, api_key, model, data, content_type, instruction)
        content = (f"{caption}\n\n" if caption else "") + f"[Imagen recibida] {description}"
    else:
        model = agent.audio_model.strip() or "whisper-1"
        transcript = await transcribe_audio(base_url, api_key, model, data, file.filename or "audio.ogg", content_type)
        content = (f"{caption}\n\n" if caption else "") + (transcript or "[Audio sin contenido reconocible]")

    if not conversation.messages:
        conversation.title = (caption or content)[:80]
    conversation.updated_at = now_utc()
    db.add(Message(conversation_id=conversation.id, role="user", content=content, sender_type="visitor", sender_name="You"))
    db.commit()
    return await _generate_reply(db, user, conversation, agent, credentials, content)


@router.patch("/{conversation_id}/mode", response_model=ConversationDetail)
def set_conversation_mode(
    conversation_id: uuid.UUID,
    payload: ConversationModeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conversation = _conversation(db, user, conversation_id)
    conversation.mode = payload.mode
    if payload.mode == "human" and conversation.assigned_user_id is None:
        conversation.assigned_user_id = user.id
    conversation.updated_at = now_utc()
    db.commit()
    return _conversation(db, user, conversation_id)


@router.patch("/{conversation_id}/assign", response_model=ConversationDetail)
def assign_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationAssign,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conversation = _conversation(db, user, conversation_id)
    if payload.assigned_user_id is None:
        conversation.assigned_user_id = None
    else:
        member = agency_member(db, user.agency_id, payload.assigned_user_id)
        if not member:
            raise HTTPException(status_code=400, detail="That operator is not part of this agency")
        conversation.assigned_user_id = member.id
    conversation.updated_at = now_utc()
    db.commit()
    return _conversation(db, user, conversation_id)


@router.patch("/{conversation_id}/labels", response_model=ConversationDetail)
def set_conversation_labels(
    conversation_id: uuid.UUID,
    payload: ConversationLabelsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conversation = _conversation(db, user, conversation_id)
    conversation.labels = sanitize_labels(payload.labels)
    conversation.updated_at = now_utc()
    db.commit()
    return _conversation(db, user, conversation_id)


@router.post("/{conversation_id}/reply", response_model=ConversationDetail)
async def reply_as_human(
    conversation_id: uuid.UUID,
    payload: SendMessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conversation = _conversation(db, user, conversation_id)
    if conversation.mode != "human":
        raise HTTPException(status_code=409, detail="Take control of the conversation before replying")
    external_message_id = await send_channel_message(db, conversation, payload.content.strip())
    db.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=payload.content.strip(),
            sender_type="human",
            sender_name=user.name,
            external_message_id=external_message_id,
        )
    )
    conversation.updated_at = now_utc()
    db.commit()
    return _conversation(db, user, conversation_id)
