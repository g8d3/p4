# Publier el instrumento en npm → aparecer en el catálogo de paquetes de Pi

Escrito por el worker nocturno 2026-10-18 08:0xZ (R75). **Esto es una tarea de 1 minuto para el
humano y es el canal de descubrimiento más directo que queda abierto.** Nada que ver con el
shadowban de HN: no depende de reputación, solo de una credencial.

## Por qué vale dinero

El catálogo **https://pi.dev/packages** se alimenta del keyword `pi-package` en **npm**. Nuestro
`package.json` ya lo tiene, y el manifest `pi` ya apunta a `dist/companion.js`:

```json
"keywords": ["pi-package"],
"pi": { "extensions": ["./dist/companion.js"] }
```

Pero el paquete **no está publicado**: `npm view pi-web-tps-monitor` → **404**. Un usuario de Pi
que abra el catálogo (la audiencia exacta: gente que corre agentes) no puede instalarlo con un
comando, y el README del plugin es justamente el sitio donde están enlazados el paper
(https://focalis.cc/tps/) y la oferta (https://focalis.cc/audit/). Es el funnel más corto que
existe hacia el comprador del audit.

## Por qué está bloqueado (y no es culpa de nadie)

- El token de `/home/vuos/.npmrc` responde **401 Unauthorized** al pedir `/-/whoami`: está
  revocado. (El fichero está en `0600`; no se ha tocado ni se ha impreso su valor.)
- La creación de cuenta por API está cerrada por npm: `Account creation via legacy auth is
  unavailable. Please set your auth-type to "web" or visit https://www.npmjs.com/signup`.
  El registro web exige navegador + captcha + verificación de correo, así que **no lo puede
  hacer un worker** aunque el buzón `focalis@agentmail.to` sea legible.
- Faltante exacto: **(espera-llave: NPM_TOKEN)** — un token con permiso de publicación.

## Lo que YA está verificado (hecho en una copia de e095; e095 no se tocó)

Ejecutado sobre una copia limpia del árbol (`/tmp/npm-pack-check`):

| paso | resultado |
|---|---|
| `npm ci` | exit 0 |
| `npm run build` (`tsc`) | exit 0 |
| `npm pack --dry-run` | **25 ficheros, 64.6 kB** (254 kB descomprimido) |
| contenido | `dist/` (browser, companion, server, models, protocol), `src/`, `test/`, `README.md`, `LICENSE`, `package.json` |
| manifest vs las reglas de Pi | `dependencies` **vacío**; `@earendil-works/pi-coding-agent` solo en `devDependencies` + `peerDependencies: "*"` — es exactamente lo que pide `docs/packages.md` (los paquetes que provee el host no se declaran en `dependencies`) |
| higiene | el tarball **no contiene** rutas internas (`/home/vuos`, `/tmp/night`), ni claves (`sk-…`, `api_key=`). Los únicos hosts son `focalis.cc` (enlaces del README y del panel). |
| versión lista | `0.10.9` (`git` limpio en `43e10a7`) |

## El comando (1 minuto)

```bash
# 1. token de publicación (tipo "Automation" en npmjs.com → Settings → Tokens) y a ~/.npmrc:
#    //registry.npmjs.org/:_authToken=<TOKEN>
npm whoami                                  # debe imprimir el usuario

# 2. publicar (dispara `prepare` → `npm run build`; NO usar --ignore-scripts)
cd /home/vuos/code/p4/e095-tps-monitor
npm publish                                  # sin scope ⇒ público por defecto

# 3. verificar
npm view pi-web-tps-monitor version          # 0.10.9
pi install npm:pi-web-tps-monitor
```

- Si la cuenta tiene 2FA para escrituras, añade `--otp <código>`.
- El nombre **`pi-web-tps-monitor` está libre ahora mismo**: publicar también lo protege de que
  otro lo registre (un unscoped sin publicar es reclamable por cualquiera).
- Cada release futuro hay que publicarlo (`npm version patch && npm publish`); el `CHANGELOG.md`
  del repo ya está al día.

## Mejora opcional (2 minutos más, mejora el clic en el catálogo)

`docs/packages.md` acepta `pi.image` / `pi.video` para la tarjeta del catálogo. Hoy no hay
ninguna. Una captura del panel en `https://focalis.cc/assets/…` + `"pi": { "extensions": [...],
"image": "https://focalis.cc/assets/tps-monitor.png" }` haría que el listado enseñe el producto
en vez de solo un nombre. **Requiere editar `e095-tps-monitor/package.json`** (carril del otro
agente esta noche); por eso queda escrito aquí y no hecho.

## Lo que NO hay que hacer

- No publicar desde el árbol sucio de otra tanda: publicar lo que hay en `43e10a7` (0.10.9) es lo
  verificado arriba.
- No cambiar `pi-web-tps-monitor` por un nombre con scope sin actualizar el README y el repo: el
  nombre aparece en la URL de instalación que la gente copia.
