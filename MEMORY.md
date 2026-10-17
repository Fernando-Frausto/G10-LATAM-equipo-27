# MEMORY.md - Análisis de Comunidad con IA (Código Unificado)
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.

## Estado actual
- **Sincronización Discord y Evaluación IA:** Ingesta bajo demanda (`POST /api/v1/discord/sync`), evaluación individual (`POST /api/v1/ai/evaluate-message`) y por lotes (`POST /api/v1/ai/evaluate-batch`) con 3 cerebros (Groq, Gemma, Gemini). Corregido mapeo de métricas en sync (`total_recibidas`, `guardadas_nuevas`) y soporte de fallback universal para `VITE_API_URL` y `VITE_MOTOR_API_URL` en todo el frontend.
- **Frontend Transparente (Messages.tsx):** Mensajes en ingesta/crudos muestran estrictamente `⏳ Pendiente por Analizar` sin datos artificiales de IA. Mensajes evaluados muestran `👍 Analizado con IA` con sus métricas reales.
- **Frontend Intuitivo y 100% Funcional (Messages.tsx - Spec 008):** Eliminado botón duplicado de sincronización de Discord, retirado botón muerto 'Añadir interacción' y checkboxes huérfanos. Corregido filtro de 'Descartados' para poder consultarlos y restaurarlos con botón `RotateCcw` esmeralda (`markCuration(id, 'pending')`). Deshabilitación preventiva en descartados para 'Analytics' y 'Evaluar IA'. Navegación resiliente a Analytics sin excepciones en mensajes evaluados. Métricas de Estado Discord unificadas ('Pendientes en Copy' e 'Incidentes prioritarios' con exclusión estricta de bots). Filtro de etapas alineado con el pipeline (`Todas Todo + Completos`, `Pendientes de Evaluar`, `Pendientes de Copy`, `Solo Completos`). Insignias: `⏳ Falta análisis con IA` (crudos), `✍️ Falta redacción de copy` (analizados esperando a Enoc), `✅ Listo / Aprobado` y `🚫 Descartado`.
- **Dashboard 100% Funcional y Reconciliado (Dashboard.tsx - Spec 009):** Reemplazado placeholder estático provisional por `<FeaturedStories key={analyticsVersion} />` interactivo con historias en vivo, citas reales, carrusel resiliente (`disabled={stories.length <= 1}`) y botones activos a `/messages` y `/approvals`. Botón "Actualizar datos" sincroniza sincrónicamente KPIs, gráficos y carrusel mediante `analyticsVersion`. Reconciliada métrica `total_audience` (10 miembros humanos reales excluyendo bots) vía fallback `author_id = author_id or autor` en puente. Null safety y formato de variaciones neutras (`0% esta semana` / `0 puntos`) en las 6 tarjetas de KPIs.
- **Caché TTL y Optimización del Dashboard:** TTL de 15s en `puente_motor_ia.py`. Carga reducida de 30-90s a ~1.5s inicial y <20ms subsecuente.
- **Tests y Calidad:** 78 pruebas al 100% en verde (`pytest tests/ -v`). Compilación limpia (`npm run build`). Inmutabilidad de los 17 archivos `.py` de la raíz, `backend/` y `motor-ia/`.

## Decisiones (y por qué)
- **Eliminación de Tecnicismos y Redundancias:** 'Curaduría' confunde a usuarios no técnicos. La insignia ahora describe el estado real del trabajo pendiente (IA o redacción de copy de Enoc). Se removió 'Actualizar' ya que el streaming de 5s y las acciones en la UI autorefrescan los datos.
- **Permiso Explícito de Modificación:** El usuario autorizó formalmente modificar frontend y adaptadores para usabilidad integral.
- **Caché TTL Inteligente (15s):** El servicio del dashboard realiza 15+ subconsultas y múltiples componentes frontend llaman en paralelo; la caché elimina más de 90 conexiones SSL redundantes a Supabase y bloqueos de SQLite sin desactualizar datos ante mutaciones (`invalidar_cache_supabase`).
- **Aislamiento Constitucional:** Cero modificaciones a código base existente de la raíz ni backend/; unificación encapsulada en puente no invasivo y cliente tipado de frontend (`communityLive.ts`).
- **Resiliencia con Fallback Fluido:** Frontend consume endpoints en vivo pero mantiene resiliencia automática ante caídas de backend o modo demo.
- **Soberanía Humana (HITL):** Los estados y textos editados por humanos (`copy_final`) prevalecen sobre el motor de IA.

## Errores a evitar
- Nunca modificar los archivos preexistentes de la raíz, `backend/` ni `motor-ia/`.
- Nunca saltarse el flujo formal (SDD) ni asumir que un cambio es "demasiado pequeño".
- Nunca hacer push directo a `main` (Regla 1). Todo el trabajo se mantiene en ramas `feature/`.
- Nunca escribir credenciales en código duro (Regla 4).
