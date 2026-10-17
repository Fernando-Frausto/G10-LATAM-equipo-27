# Especificación 010: Unificación de Pestañas de Navegación y Flujo de Equipo

## 1. Contexto y Propósito

### ¿Qué se busca lograr?
Unificar de forma universal el menú de navegación lateral (`frontend/src/components/Sidebar.tsx`) para todos los roles de usuario (`admin`, `community_manager`, `reviewer`), consolidando estrictamente las **6 pestañas esenciales** que conforman el flujo de trabajo colaborativo real del equipo:
1. **Dashboard** (`/dashboard`)
2. **Ingesta de mensajes** (`/messages` — renombrada desde "Mensajes" / "Ingesta Discord" para alinearse con el título principal de la vista)
3. **Análisis** (`/analytics`)
4. **Redacción de contenidos** (`/content` — módulo de copywriting para Enoc, antes rotulado "Content Studio")
5. **Aprobaciones** (`/approvals`)
6. **Informes y Almacenamiento** (`/oci-storage` — módulo de OCI y reportes para Tania, antes rotulado "OCI Storage")

Asimismo, se garantiza en `frontend/src/App.tsx` que todos los roles autenticados tengan acceso irrestricto a estas 6 rutas principales, saneando rigurosamente importaciones y variables no utilizadas en `Sidebar.tsx` para evitar fallos de TypeScript (`TS6133`), eliminando el bloque residual de administración del menú lateral, y redirigiendo la ruta raíz `/` hacia `/dashboard` para asegurar el resaltado activo consistente del menú.

### ¿Por qué es necesario?
1. **Eliminación de Disparidad entre Roles:** Actualmente existe una bifurcación en `Sidebar.tsx` donde únicamente el rol `community_manager` visualizaba un menú limpio de 6 opciones, mientras que al iniciar sesión con `admin` o `reviewer` (ej. `admin@cloudedtech.com`) se desplegaba una lista desbordada de 15 enlaces (`Historias destacadas`, `Hashtags`, `Audiencia`, `Calendar`, `Export`, `My Reports`, `Auditoría`, etc.), generando confusión y fragmentación en la experiencia del usuario.
2. **Alineación con el Flujo Real del Equipo:** La operación diaria del equipo CloudEdTech se divide en etapas claras:
   - Ingesta y captura de mensajes de Discord (`/messages`).
   - Evaluación y enriquecimiento con IA (`/analytics`).
   - Redacción de copys por parte de Enoc (`/content`).
   - Revisión y aprobación humana HITL (`/approvals`).
   - Consolidación de reportes y almacenamiento OCI a cargo de Tania (`/oci-storage`).
   - Visión directiva agregada en el Dashboard (`/dashboard`).
   Cualquier otra pestaña secundaria desvía la atención del flujo operativo central.
3. **Estandarización Terminológica:** La vista de mensajes titula en su encabezado `<h2>Ingesta de mensajes</h2>`, pero el menú mostraba inconsistentemente `"Mensajes"` o `"Ingesta Discord"`. Además, términos en inglés como `"Content Studio"` y `"OCI Storage"` resultaban ajenos a la nomenclatura en español adoptada por el equipo ("Redacción de contenidos" e "Informes y Almacenamiento").
4. **Saneamiento Estricto de Código y Prevención de Errores TypeScript (`TS6133`):** Dado que `frontend/tsconfig.app.json` impone `"noUnusedLocals": true`, el retiro de las pestañas secundarias y del bloque de administración exige purgar todos los iconos no utilizados (`Star`, `Hash`, `Users`, `CalendarDays`, `Download`, `FileClock`, `FileText`, `ShieldCheck`, `Settings`) y la variable `isCommunityManager`. Conservar únicamente los 8 iconos activos previene fallos bloqueantes en la compilación de producción.
5. **Desbloqueo de Acceso para Revisoras en OCI Storage:** En `frontend/src/App.tsx`, la ruta `/oci-storage` solo autorizaba a `admin` y `community_manager`. Al incorporar el rol `reviewer` en `allowedRoles`, se asegura que Tania y cualquier revisor puedan consultar y operar sus informes y almacenamiento sin bloqueos de autorización.
6. **Consistencia Visual en Ruta Raíz (`/`):** Al navegar a la raíz `/`, si se renderiza `<Dashboard />` directamente sin redirección de URL, el enlace `<SidebarItem to="/dashboard">` no activa su clase de resaltado naranja (`bg-orange-500`). Redirigir de `/` a `/dashboard` garantiza una indicación visual activa impecable desde el primer instante.
7. **Cumplimiento Constitucional e Inmutabilidad:** Cero modificaciones a los 17 archivos `.py` de la raíz, `backend/` ni `motor-ia/`. Toda la intervención se concentra exclusivamente en `frontend/src/components/Sidebar.tsx` y `frontend/src/App.tsx`.

---

## 2. Requerimientos Funcionales (Formato EARS)

### RF-01: Unificación Universal del Menú Lateral y Saneamiento Estricto en `Sidebar.tsx`
- **QUÉ:**
  - **CUANDO** cualquier usuario autenticado (sin importar si su rol es `admin`, `community_manager` o `reviewer`) visualice el menú de navegación lateral (`frontend/src/components/Sidebar.tsx`), **EL SISTEMA DEBERÁ** desplegar unificada y exclusivamente las siguientes 6 pestañas operativas en la sección "Principal":
    1. **Dashboard** (`/dashboard`, icono `Home`)
    2. **Ingesta de mensajes** (`/messages`, icono `MessageSquare`)
    3. **Análisis** (`/analytics`, icono `BarChart3`)
    4. **Redacción de contenidos** (`/content`, icono `WandSparkles`)
    5. **Aprobaciones** (`/approvals`, icono `CheckCircle`)
    6. **Informes y Almacenamiento** (`/oci-storage`, icono `CloudUpload`)
  - **EL SISTEMA DEBERÁ** erradicar la bifurcación condicional basada en `isCommunityManager` que proyectaba menús dispares y 15 pestañas desordenadas para cuentas con rol `admin` o `reviewer`.
  - **EL SISTEMA DEBERÁ** retirar íntegramente del menú lateral visible:
    - Las pestañas secundarias: `/highlights`, `/hashtags`, `/audience`, `/calendar`, `/export`, `/my-reports`.
    - La sección completa de administración: bloque `{user?.role === 'admin' && (<p>Administración</p>...)}` con sus rutas `/audit`, `/security`, `/settings`.
  - **EL SISTEMA DEBERÁ** preservar la estructura del contenedor `<nav className="min-h-0 flex-1 overflow-y-auto px-4 py-5">` garantizando desplazamiento vertical fluido e independiente tanto en escritorio como en dispositivos móviles.
  - **EL SISTEMA DEBERÁ** sanear estrictamente las importaciones de `Sidebar.tsx`:
    - Eliminar los 9 iconos huérfanos de `lucide-react`: `Star`, `Hash`, `Users`, `CalendarDays`, `Download`, `FileClock`, `FileText`, `ShieldCheck`, `Settings`.
    - Retener estrictamente los 8 iconos activos: `Home`, `MessageSquare`, `BarChart3`, `WandSparkles`, `CheckCircle`, `CloudUpload`, `LogOut`, `X`.
    - Suprimir la variable no utilizada `isCommunityManager`.
- **POR QUÉ:**
  - Para erradicar la sobrecarga visual, unificar la navegación en el flujo operativo del equipo y garantizar el cumplimiento de `"noUnusedLocals": true` sin arrojar errores `TS6133` en TypeScript.

### RF-02: Estandarización de la Etiqueta "Ingesta de mensajes"
- **QUÉ:**
  - **CUANDO** el menú lateral renderice el elemento correspondiente a la ruta `/messages`, **EL SISTEMA DEBERÁ** mostrar de forma homogénea la etiqueta textual `"Ingesta de mensajes"`.
  - **EL SISTEMA DEBERÁ** suprimir las denominaciones discordantes previas (`"Mensajes"` e `"Ingesta Discord"`).
- **POR QUÉ:**
  - Para unificar la terminología con el encabezado oficial de la pantalla (`<h2>Ingesta de mensajes</h2>` en `frontend/src/pages/Messages.tsx`), eliminando discrepancias entre el menú y el contenido de la vista.

### RF-03: Homogeneización de Nomenclatura del Flujo Editorial y Almacenamiento
- **QUÉ:**
  - **CUANDO** el menú lateral renderice el enlace a `/content`, **EL SISTEMA DEBERÁ** desplegar `"Redacción de contenidos"` como etiqueta para todos los roles, descartando el rótulo anglicista `"Content Studio"`.
  - **CUANDO** el menú lateral renderice el enlace a `/oci-storage`, **EL SISTEMA DEBERÁ** desplegar `"Informes y Almacenamiento"` como etiqueta para todos los roles, descartando el rótulo `"OCI Storage"`.
- **POR QUÉ:**
  - Para brindar claridad semántica en español sobre los módulos asignados a Enoc (redacción de copys) y a Tania (informes de comunidad y almacenamiento en Oracle Cloud).

### RF-04: Acceso Universal de Roles a las 6 Rutas Principales en `App.tsx`
- **QUÉ:**
  - **CUANDO** cualquier usuario autenticado con rol `admin`, `community_manager` o `reviewer` navegue a cualquiera de las 6 rutas principales (`/dashboard`, `/messages`, `/analytics`, `/content`, `/approvals`, `/oci-storage`), **EL SISTEMA DEBERÁ** otorgar acceso inmediato y sin restricciones de rol a la pantalla solicitada.
  - **EL SISTEMA DEBERÁ** asegurar que la ruta `/oci-storage` en `frontend/src/App.tsx` permita explícitamente el acceso a los roles `["admin", "community_manager", "reviewer"]`.
  - **EL SISTEMA DEBERÁ** mantener intactas las protecciones de rol existentes (`RoleProtectedRoute`) para las rutas auxiliares secundarias (`/highlights`, `/hashtags`, etc., y `/audit`, `/security`, `/settings`).
- **POR QUÉ:**
  - Para evitar bloqueos de autorización que impidan a Tania o a cualquier miembro con rol revisor operar en el módulo de Informes y Almacenamiento, manteniendo protegidas las rutas auxiliares.

### RF-05: Redirección Canónica de Raíz (`/`) y Preservación de Rutas Auxiliares
- **QUÉ:**
  - **CUANDO** el usuario acceda a la ruta raíz `/` de la aplicación, **EL SISTEMA DEBERÁ** redirigir canónicamente mediante `<Navigate to="/dashboard" replace />`, asegurando que la URL activa sea siempre `/dashboard` y el elemento "Dashboard" en el Sidebar active su estilo de selección (`bg-orange-500 text-white`).
  - **SI** un usuario con rol autorizado introduce manualmente en el navegador la URL de una ruta secundaria preexistente (como `/highlights`, `/hashtags`, `/audience`, `/calendar`, `/export`, `/my-reports`, `/audit`, `/security`, `/settings`), **EL SISTEMA DEBERÁ** mantener la definición de estas rutas en `frontend/src/App.tsx` para no romper enlaces profundos o utilidades administrativas.
  - **SI** un usuario introduce una ruta inexistente o sin autorización, **EL SISTEMA DEBERÁ** ejecutar la redirección de contingencia hacia `/dashboard`.
- **POR QUÉ:**
  - Para brindar una experiencia de navegación limpia y un estado activo predecible en el menú lateral, preservando la robustez de rutas auxiliares.

### RF-06: Inmutabilidad Constitucional y Verificación de Calidad
- **QUÉ:**
  - **EN TODO MOMENTO**, **EL SISTEMA DEBERÁ** mantener estrictamente inalterados los 17 archivos `.py` preexistentes en la raíz del proyecto, así como todo el código en las carpetas `backend/` y `motor-ia/`.
  - **EL SISTEMA DEBERÁ** concentrar las modificaciones exclusivamente en:
    1. `frontend/src/components/Sidebar.tsx`
    2. `frontend/src/App.tsx`
  - **CUANDO** se ejecute la suite de pruebas del backend (`pytest tests/ -v`), **EL SISTEMA DEBERÁ** certificar el 100% de las pruebas preexistentes en verde.
  - **CUANDO** se compile el cliente web (`npm run build` en `frontend/`), **EL SISTEMA DEBERÁ** compilar de forma estricta con 0 errores de TypeScript y empaquetado exitoso.
- **POR QUÉ:**
  - En estricto cumplimiento de las Reglas 2, 3 y 6 de la Constitución (`docs/constitution.md`).

---

## 3. Restricciones y Cumplimiento Constitucional

1. **Inviolabilidad del Main (Regla 1):** Todo el trabajo se mantiene sobre la rama funcional de desarrollo (`unificacion-beta`), sin push directo a `main`.
2. **Aislamiento de Interfaz (Regla 2):** Toda la lógica de menús, etiquetas, navegación y protección de rutas permanece confinada en el frontend (`Sidebar.tsx` y `App.tsx`).
3. **Retrocompatibilidad Obligatoria (Regla 3):** No se alteran las rutas URL existentes (`/dashboard`, `/messages`, `/analytics`, `/content`, `/approvals`, `/oci-storage`), preservando la compatibilidad de marcadores y redirecciones.
4. **Seguridad de Secretos (Regla 4):** Cero credenciales ni datos sensibles en componentes o configuración.
5. **Control de Dependencias (Regla 5):** Reutilización estricta de las librerías existentes (`lucide-react`, `react-router-dom`). No se introducen paquetes externos.
6. **Diseño Test-First y Verificación Integral (Regla 6):** Verificación exhaustiva de compilación (`npm run build`) y pruebas automatizadas (`pytest tests/ -v`) antes del pase a producción.

---

## 4. Criterios de Aceptación Globales

- [ ] El menú lateral (`Sidebar.tsx`) muestra exactamente las mismas 6 pestañas operativas para cualquier usuario autenticado (`admin`, `community_manager`, `reviewer`):
  1. Dashboard (`/dashboard`)
  2. Ingesta de mensajes (`/messages`)
  3. Análisis (`/analytics`)
  4. Redacción de contenidos (`/content`)
  5. Aprobaciones (`/approvals`)
  6. Informes y Almacenamiento (`/oci-storage`)
- [ ] Se eliminó la bifurcación condicional basada en `isCommunityManager` en `Sidebar.tsx`.
- [ ] Se eliminó completamente la sección visible de "Administración" (`/audit`, `/security`, `/settings`) del menú lateral.
- [ ] Ya no se renderizan en el menú lateral las 9 pestañas secundarias o desordenadas (`/highlights`, `/hashtags`, `/audience`, `/calendar`, `/export`, `/my-reports`, `/audit`, `/security`, `/settings`).
- [ ] Se eliminaron de `Sidebar.tsx` los 9 iconos no utilizados (`Star`, `Hash`, `Users`, `CalendarDays`, `Download`, `FileClock`, `FileText`, `ShieldCheck`, `Settings`) y la variable `isCommunityManager`, previniendo errores `TS6133`.
- [ ] Solo se importan y utilizan los 8 iconos activos: `Home`, `MessageSquare`, `BarChart3`, `WandSparkles`, `CheckCircle`, `CloudUpload`, `LogOut`, `X`.
- [ ] La pestaña correspondiente a `/messages` tiene el rótulo unificado `"Ingesta de mensajes"` con el icono `MessageSquare`.
- [ ] La pestaña correspondiente a `/content` tiene el rótulo `"Redacción de contenidos"` con el icono `WandSparkles`.
- [ ] La pestaña correspondiente a `/oci-storage` tiene el rótulo `"Informes y Almacenamiento"` con el icono `CloudUpload`.
- [ ] En `App.tsx`, la ruta `/oci-storage` autoriza a los roles `["admin", "community_manager", "reviewer"]`.
- [ ] Un usuario con rol `reviewer` puede acceder y operar fluidamente en `/oci-storage` sin redirecciones bloqueantes.
- [ ] La ruta raíz `/` redirige canónicamente a `/dashboard` con `<Navigate to="/dashboard" replace />`, manteniendo activo el ítem "Dashboard" en el Sidebar (`bg-orange-500`).
- [ ] Las rutas secundarias preexistentes se mantienen definidas en `App.tsx` para navegación directa por URL sin romper la aplicación.
- [ ] Los 17 archivos `.py` de la raíz, `backend/` y `motor-ia/` permanecen 100% inalterados.
- [ ] La suite de pruebas del backend (`pytest tests/ -v`) permanece 100% en verde.
- [ ] La compilación del frontend (`npm run build`) finaliza con 0 errores de TypeScript.
