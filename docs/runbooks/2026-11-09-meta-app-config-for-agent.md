# Meta app configuration: task for a browser agent

Paste everything below the line into an agent with browser access (ChatGPT Work / operator mode).
It needs the user's own Facebook session already active in that browser.

---

## Objective

Configure the Meta app **fast-livery** (App ID `1074725462274330`) so that the Instagram
OAuth dialog stops failing with `El dominio de esta URL no está incluido en los dominios de la app`
and the product can connect an Instagram Business account.

Do not create accounts, do not publish the app, do not start App Review, do not touch the
App Secret, do not change the Facebook password or 2FA.

## Starting page

`https://developers.facebook.com/apps/1074725462274330/settings/basic/`

## Step 1: declare the app domain

1. On **Configuración de la app → Básica**, find the field **Dominios de la app**.
2. Write `fast-livery.r3soluciones.com` — no scheme, no trailing slash, no path.
3. Verify these fields already have a value; if empty, fill them:
   - **URL de la política de privacidad**: `https://fast-livery.r3soluciones.com/privacy`
   - **URL de Condiciones del servicio**: `https://fast-livery.r3soluciones.com/terms`
   - **Eliminación de datos de usuario** → *URL de instrucciones*: `https://fast-livery.r3soluciones.com/data-deletion`
4. Press **Guardar cambios**.
5. Reload the page and confirm **Dominios de la app** is no longer empty. This is the acceptance
   test for step 1; a toast is not enough.

## Step 2: allow the OAuth redirect

1. Open `https://developers.facebook.com/apps/1074725462274330/fb-login/settings/`
   (menú: **Iniciar sesión con Facebook → Configuración**).
2. In **URI de redirección de OAuth válidos**, press *Agregar URI* and add
   `https://fast-livery.r3soluciones.com/api/instagram/oauth/callback`
3. Confirm **Inicio de sesión con OAuth del navegador** and **Inicio de sesión con OAuth web**
   are enabled.
4. Press **Guardar cambios** and reload to confirm the URI is listed.

## Step 3: permissions for Instagram

1. Open `https://developers.facebook.com/apps/1074725462274330/use_cases`.
2. If the Instagram use case is missing, press **Agregar casos de uso** and add the one for
   Instagram (publishing, stories, comments and direct messages).
3. Open **Personalizar → Permisos y funciones**. There is no save button: Meta applies each
   change when marked. The confirmation is the **Estado** column showing `Listo para la prueba`.
4. Ensure these are added:
   `instagram_basic`, `instagram_content_publish`, `instagram_manage_messages`,
   `instagram_manage_comments`.
5. If publishing to a Facebook Page will be used, also add the use case
   **Administrar todos los aspectos de tu página** with `pages_show_list`, `pages_manage_posts`,
   `business_management`.

## Step 4: testers, only if the person is not an admin

1. `https://developers.facebook.com/apps/1074725462274330/roles/roles/`
2. If the account that will connect Instagram already appears as **Administrador**, skip this step.
3. Otherwise press **Agregar personas → Evaluador** and add that Facebook account.
4. Do not use **Usuarios de prueba**: those accounts have no Instagram Business or Page.

## Step 5: acceptance test

1. Open
   `https://fast-livery.r3soluciones.com/clients/9b2ac520-7c1d-4f18-8346-40db24e93081/channels/instagram-config`
2. Log in with `dhemian@gmail.com` if the session expired.
3. In block **4 · Conectar la cuenta del cliente**, press **Conectar con Instagram**.
4. Expected: a new window opens showing the **Facebook login**, not the wrench error page.
5. Do not complete the login; stop here and report.

## If it fails

Report the exact text of the error and the URL shown in the failure page. Common causes:

| Error | Cause |
|---|---|
| `El dominio de esta URL no está incluido en los dominios de la app` | Step 1 not saved, or not propagated (wait 2–10 min) |
| `URL Blocked: This redirect failed because the redirect URI is not whitelisted` | Step 2 missing |
| `App not active` | The account is not a tester and is not an admin |
| `Invalid Scopes` | Step 3 missing a permission |

## What to report back

For each step: the field value before and after, whether the reload confirmed it, and a
screenshot of the final state. End with the result of Step 5 and the exact error text if any.

## Never do

- Publish the app or start App Review.
- Reveal or change the App Secret.
- Create, rename or delete Facebook accounts or Pages.
- Change passwords, 2FA or business verification data.
