# Tareas de Implementación: Spec 010
## Unificación de Pestañas de Navegación y Flujo de Equipo

---

### [x] Tarea 1: Refactorización y Saneamiento en `Sidebar.tsx`
- **RF Asociado:** RF-01, RF-02, RF-03, RF-06
- **Estimación:** ~20 minutos
- **Archivos a modificar:** `frontend/src/components/Sidebar.tsx`
- **Descripción:**
  1. Depurar las importaciones de `lucide-react`:
     - Retirar los 9 iconos huérfanos: `CalendarDays`, `Download`, `FileClock`, `FileText`, `Hash`, `Settings`, `ShieldCheck`, `Star`, `Users`.
     - Conservar únicamente los 8 iconos activos: `BarChart3`, `CheckCircle`, `CloudUpload`, `Home`, `LogOut`, `MessageSquare`, `WandSparkles`, `X`.
  2. Eliminar la variable no utilizada `isCommunityManager` para prevenir errores `TS6133`.
  3. Suprimir toda la bifurcación condicional `isCommunityManager ? (...) : (...)` y el bloque condicional `{user?.role === 'admin' && (<p>Administración</p>...)}`.
  4. Renderizar de forma directa y universal las 6 pestañas operativas en la sección `"Principal"`:
     - `Dashboard` (`/dashboard`, icono `Home`)
     - `Ingesta de mensajes` (`/messages`, icono `MessageSquare`)
     - `Análisis` (`/analytics`, icono `BarChart3`)
     - `Redacción de contenidos` (`/content`, icono `WandSparkles`)
     - `Aprobaciones` (`/approvals`, icono `CheckCircle`)
     - `Informes y Almacenamiento` (`/oci-storage`, icono `CloudUpload`)
  5. Mantener la estructura del contenedor `<nav className="min-h-0 flex-1 overflow-y-auto px-4 py-5">` para un desplazamiento vertical limpio en móviles y escritorio.
- [x] **Hecho cuando:**
  En `Sidebar.tsx` ya no existan iconos ni variables huérfanas, no exista bifurcación por rol y cualquier usuario autenticado visualice estrictamente las 6 pestañas unificadas del flujo de equipo con la denominación `"Ingesta de mensajes"`.

---

### [x] Tarea 2: Actualización de Rutas, Redirección Canónica y Permisos en `App.tsx`
- **RF Asociado:** RF-04, RF-05, RF-06
- **Estimación:** ~20 minutos
- **Archivos a modificar:** `frontend/src/App.tsx`
- **Descripción:**
  1. En la ruta raíz `/`, sustituir `<Route path="/" element={<Dashboard />} />` por:
     `<Route path="/" element={<Navigate to="/dashboard" replace />} />`.
  2. Agrupar la ruta `/oci-storage` dentro del bloque `RoleProtectedRoute` de `allowedRoles={["admin", "reviewer", "community_manager"]}` junto con `/analytics`, `/content` y `/approvals`.
  3. Eliminar el bloque redundante que restringía `/oci-storage` a solo `admin` y `community_manager`.
  4. Verificar que las rutas auxiliares (`/highlights`, `/hashtags`, etc., y `/audit`, `/security`, `/settings`) se mantengan declaradas para acceso directo por URL de administradores o revisores.
- [x] **Hecho cuando:**
  Al ingresar a la raíz `/` se redirija automáticamente a `/dashboard` activando el estilo naranja del menú, y un usuario con rol `reviewer` pueda ingresar y operar directamente en `/oci-storage` sin denegaciones ni redirecciones.

---

### [x] Tarea 3: Verificación Global de Calidad, Tipado e Inmutabilidad
- **RF Asociado:** RF-06
- **Estimación:** ~20 minutos
- **Archivos a modificar:** Ninguno (validación y control de calidad)
- **Descripción:**
  1. Ejecutar la compilación del frontend con `npm run build` en el directorio `frontend/`, certificando código de salida 0 sin errores de TypeScript (`TS6133`, `TS2304`, etc.).
  2. Ejecutar la suite completa de pruebas del backend con `pytest tests/ -v`, comprobando que el 100% de los tests (77 o 78 tests) continúen pasando en verde.
  3. Ejecutar `git status` y verificar que los 17 archivos preexistentes en la raíz, la carpeta `backend/` y `motor-ia/` permanezcan 100% inalterados.
- [x] **Hecho cuando:**
  El build del frontend culmine con 0 errores de compilación, todas las pruebas del backend pasen en verde y se certifique la total inmutabilidad de los módulos protegidos por la Constitución.
