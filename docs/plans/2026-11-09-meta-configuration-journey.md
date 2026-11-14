# The Meta configuration journey

Three screens configure Meta today: platform settings, the channel screen with its
advanced form, and the guided wizard. This is the single path that replaces them.

## The rule

One owner per fact.

| Fact | Owner | Where |
|---|---|---|
| App ID and App Secret | The agency, once | `Configuración → Meta` |
| Permissions and app review | The agency, once | Meta, linked from `Configuración → Meta` |
| Business verification | The agency, once | Meta, linked from `Configuración → Meta` |
| WhatsApp number, WABA, token | Each client | Client wizard, WhatsApp |
| Instagram account, Page, token | Each client | Client wizard, Instagram |
| Webhook callback and verify token | Each client, values from the platform | Client wizard, per channel |

## The journey

### Once per agency

1. `Configuración → Meta` → save App ID and App Secret. Verified against Meta.
2. Same screen → open the app in Meta for the four permissions of each channel.
3. Same screen → start App Review; it is the only step that cannot be automated.
4. Business verification, when Meta asks for it.

Nothing else about Meta belongs to the agency screen.

### Once per client

5. Client → Channels → pick the channel: WhatsApp or Instagram.
6. Wizard step 1: connect the account with OAuth. The result is a client token,
   not a shared one.
7. Wizard step 2: choose the number or the Page from what Meta returned.
8. Wizard step 3: copy the callback URL and verify token that the wizard shows,
   paste them in Meta, subscribe `messages` and, for Instagram, `comments`.
9. Wizard step 4: send the test message or publish the test post.

If an agency step is missing, the client wizard shows one line saying so and a link
to the agency screen. It never shows the agency values.

## What disappears

| Element | Reason |
|---|---|
| `Configuración avanzada (BYO)` on the channel screen | It duplicates the wizard and lets anyone paste credentials that bypass the checks |
| The mock credentials stored in the channel | They show green steps with no real account |
| The guide accordion on the channel | Replaced by the wizard, already removed |
| The second entry to the same form | Two buttons, one destination |

The advanced form survives only as an explicit escape hatch behind the wizard, for
a client that insists on its own app, and it must be emptied by a migration rather
than left with example values.

## Order of work

| Step | Work | Days |
|---|---|---|
| 1 | Clear the mock values from existing channel rows | 0.5 |
| 2 | Move the advanced form behind the wizard and empty its defaults | 1 |
| 3 | Wizard for WhatsApp with the same four steps as Instagram | 2 |
| 4 | Agency screen links the four permissions and the review per channel | 1 |
| 5 | One shared component so both wizards cannot drift | 2 |
