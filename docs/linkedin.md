# LinkedIn: generar, aprobar y publicar

Fast Livery genera posts y reescrituras de perfil por cliente. Para perfiles personales también puede publicar texto con la API oficial **Share on LinkedIn**. Nunca publica automáticamente: una persona debe revisar el texto exacto, marcar la autorización y pulsar **Publicar texto aprobado**.

No se usan cookies, scraping ni automatización del navegador.

## Alcance actual

- Perfil personal: OAuth 2.0 y publicación de texto con `w_member_social`.
- Copy: 21 fórmulas de hook, voz por cliente y humanizador local.
- Perfil: rúbrica de 12 componentes / 100 y propuesta de Titular + Acerca de para copiar.
- Respaldo: copiar/pegar funciona aunque OAuth no esté configurado.
- Auditoría: el borrador conserva estado, ID externo y fecha de publicación.

No incluye imágenes, programación, comentarios, DMs ni páginas de empresa. Publicar como Página requiere Community Management API y aprobación adicional de LinkedIn. La API tampoco permite aplicar libremente el Titular o Acerca de; esos cambios siguen siendo manuales.

## Configuración del operador

1. Crea una app en [LinkedIn Developer](https://www.linkedin.com/developers/apps) y asóciala con una Página de LinkedIn administrada por tu organización.
2. En **Products**, activa:
   - Sign In with LinkedIn using OpenID Connect.
   - Share on LinkedIn.
3. En **Auth**, registra exactamente:

   `https://TU-DOMINIO/api/linkedin/oauth/callback`

   Para desarrollo local, usa el mismo origen público definido en `FRONTEND_URL`, por ejemplo:

   `http://localhost:3001/api/linkedin/oauth/callback`

4. Configura el servidor:

   ```env
   LINKEDIN_CLIENT_ID=...
   LINKEDIN_CLIENT_SECRET=...
   LINKEDIN_OAUTH_REDIRECT_PATH=/api/linkedin/oauth/callback
   LINKEDIN_API_VERSION=202601
   ```

5. Reconstruye o reinicia API y web. El endpoint `/api/linkedin/oauth/options` debe indicar `oauth_available: true`.

`LINKEDIN_API_VERSION` es explícito porque LinkedIn versiona mensualmente su Marketing API. Revisa las versiones soportadas antes de desplegar.

## Flujo del usuario

1. Canales → LinkedIn → elegir cliente.
2. **Conectar con LinkedIn**.
3. Autorizar `openid`, `profile` y `w_member_social`.
4. Generar desde un hecho verdadero específico.
5. Editar el bloque final.
6. Marcar “Revisé este texto exacto”.
7. Pulsar **Publicar texto aprobado**.

El mismo proceso está explicado dentro de Playground → Manual → **LinkedIn: generar, aprobar y publicar**.

## IA y seguridad

El proveedor de redacción se resuelve con las claves de la agencia en este orden: Moonshot → DeepSeek → OpenAI → DashScope. Sin clave, se usa un fallback local. El humanizador corre localmente.

Los tokens OAuth se cifran en base de datos, nunca vuelven en la respuesta API y quedan aislados por Agency → Client. El endpoint de publicación exige aprobación explícita y es idempotente: volver a enviar el mismo borrador publicado devuelve el mismo ID sin duplicarlo.

Para pruebas locales:

```env
LINKEDIN_MOCK_MODE=true
```

Formulas, lexicon and humanizer are adapted under MIT from [linkedin-agent-skill](https://github.com/Jakeschincariol/linkedin-agent-skill) and live under `apps/api/app/services/linkedin/`.
