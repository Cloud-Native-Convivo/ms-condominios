# Diseño: recurso `Unidad` en `ms-condominios`

**Fecha:** 2026-10-15
**Alcance:** exclusivo a `ms-condominios/`. No toca `ms-gastos-comunes`, `ms-espacios-comunes`, BFF ni frontends.
**Contexto más amplio:** primer sub-proyecto de dos. El segundo (`ms-usuario`, gestión de usuarios/roles por condominio) queda para un ciclo de diseño posterior, una vez que esta interfaz esté implementada y verificada.

## 1. Motivación

`ms-usuario` necesitará validar que una asociación usuario-unidad referencie una unidad real. Hoy `Unidad` (torre/piso/número) no existe como entidad en ningún microservicio: `ms-condominios` solo modela `Condominio`; `ms-gastos-comunes.GastoComun.unidadId` y el claim `unidad_id` de Entra ID son strings/claims sueltos sin catálogo que los respalde (documentado como limitación conocida en `ms-gastos-comunes/README.md`, sección "Decisiones y limitaciones conocidas").

Decisión de alcance tomada antes de este diseño: `Unidad` vive en `ms-condominios` (sub-recurso natural de `Condominio`, que ya es dueño de ese agregado) en vez de en `ms-usuario`. La validación cruzada de `ms-gastos-comunes`/`ms-espacios-comunes` contra este catálogo queda explícitamente pendiente para una etapa posterior (no es parte de este sub-proyecto).

## 2. Modelo de datos

```python
class Unidad(Base):
    __tablename__ = "unidades"
    __table_args__ = (
        Index("ix_unidades_condominio_id", "condominio_id"),
        UniqueConstraint("condominio_id", "torre", "piso", "numero", name="uq_unidad_direccion"),
    )
    id = Column(Integer, Identity(), primary_key=True)
    condominio_id = Column(Integer, ForeignKey("condominios.id", ondelete="CASCADE"), nullable=False)
    torre = Column(String(50), nullable=False, default="UNICA")
    piso = Column(String(10), nullable=False)
    numero = Column(String(20), nullable=False)
    activa = Column(Boolean, nullable=False, default=True)
```

- `torre/piso/numero`: mismos campos que el formulario mock de `Frontend-CloudNative` (`StepUnitForm`). `String`, no numérico (acepta "PH", "B", etc.).
- **Normalización (solo DTOs, no en el modelo):** `torre`, `piso`, `numero` se guardan en mayúsculas sin espacios al borde (`strip().upper()`), para que el unique constraint no deje pasar duplicados por diferencias de formato (`"a "` vs `"A"`).
- **`torre` con default `"UNICA"`:** aplica únicamente a `torre`, para condominios sin torres. `piso`/`numero` vacíos tras `strip()` se **rechazan con 422** (ya tienen `min_length=1`) — no caen a ningún valor por defecto. Un piso o número vacío es un error de entrada, no una ambigüedad resoluble.
- **`activa` (soft delete):** ver sección 4.
- Sin columnas especulativas (`alicuota`, `metraje`, `tipo_uso`): ningún consumidor actual (ni `GastoComunService` ni nada en el workspace) hace prorrateo por alícuota. Agregarlas sería YAGNI.

### Compatibilidad Oracle/Alembic verificada

- `Boolean`: `Condominio.seguro_incendio`/`plan_emergencia` ya usan `sa.Boolean()` contra Oracle Database Free 23ai (soporta `BOOLEAN` nativo desde 23c) y pasan tests de integración reales (`tests/integration/test_oracle.py`). Sin riesgo nuevo.
- `server_default=sa.true()`: mismo patrón que `Outbox.processed` (`server_default=sa.false()`) en la migración ya aplicada `0001_esquema_inicial.py:43`. Precedente directo, solo invierte el literal.
- `ForeignKey(ondelete="CASCADE")`: Oracle lo soporta nativo en DDL; SQLAlchemy lo emite correctamente para el dialecto Oracle.
- `alembic/env.py:24-25` importa cada modelo explícitamente para que `Base.metadata` los conozca (requerido para autogenerate futuro, aunque esta migración es manual). Debe agregarse `import app.model.unidad` ahí — se había omitido en el borrador anterior del plan.

## 3. Endpoints y autorización

Prefix `/condominios/{id_condominio}/unidades`, mismo patrón Router→Service→Repository que `Condominio`.

| Método | Ruta | Roles | Nota |
|---|---|---|---|
| `POST` | `/` | ADMIN | valida que el condominio exista (`CondominioService.obtener_condominio`) |
| `GET` | `/` | ADMIN | lista solo unidades `activa=true` por defecto |
| `GET` | `/{id_unidad}` | ADMIN | 404 si no existe o pertenece a otro condominio (nunca confirma existencia cruzada) |
| `PUT` | `/{id_unidad}` | ADMIN | actualización parcial; también permite reactivar (`activa: true`) |
| `DELETE` | `/{id_unidad}` | ADMIN | lógico, ver sección 4 |

**Decisión de autorización — ADMIN-only, sin `RESIDENTE`:** a diferencia de `GET /condominios/{id}` (que sí acepta `RESIDENTE`, porque expone solo datos del condominio en sí), listar/leer unidades expone estructura de ocupación sin que exista hoy ninguna forma de acotarlo a "la unidad propia del residente" (eso es justamente lo que `ms-usuario`, etapa 2, resolverá). Dar lectura abierta sin esa validación sería ampliar permisos sin justificación. Se revisa cuando `ms-usuario` defina cómo valida la unidad propia durante el registro.

### Riesgo de suplantación (A01 OWASP) — heredado, documentado, no corregido en este sub-proyecto

`app/middleware/auth_roles.py:requiere_roles` confía ciegamente en el header `X-Usuario-Roles` sin verificación criptográfica — a diferencia de `ms-gastos-comunes`, que valida el JWT de forma autónoma y solo *loguea* una discrepancia con el header del BFF (nunca confía en él para autorizar). Cualquier cliente con acceso directo al puerto del servicio puede fijar `X-Usuario-Roles: ADMIN` y obtener acceso total, incluido a los endpoints de `Unidad`.

Verificado:
- Local: `docker-compose.yml` mapea `"8084:8084"` — el servicio queda expuesto directo al host.
- Prod: `terraform-cloud/` no define task/service ECS para `ms-condominios` todavía (`ms-condominios/AGENTS.md` §13) — la mitigación documentada ("nunca alcanzable sin pasar por el BFF, sin exposición directa en API Gateway ni puerto público") es una intención escrita, no algo que la infraestructura esté forzando hoy, porque el servicio no está desplegado.

Los endpoints de `Unidad` usan exactamente el mismo mecanismo que ya protege (o no protege) a `Condominio` — no agravan el riesgo, pero tampoco lo corrigen. Corregirlo (ej. validación de JWT propia, como hace `ms-gastos-comunes`) es un cambio al modelo de autorización de todo el servicio, fuera del alcance de "agregar `Unidad`" y de la instrucción explícita de no modificar otros servicios en esta etapa. Queda como mejora futura a evaluar junto con la decisión de despliegue real de `ms-condominios` (Trello #46).

## 4. Eliminación: lógica, no física

Un `DELETE` físico deja a un futuro `ms-usuario` con una asociación a un `unidad_id` que nunca existió desde su perspectiva — sin FK entre microservicios, no hay forma de detectarlo. `DELETE /unidades/{id}` pone `activa = False` en vez de borrar la fila. `PUT` con `activa: true` reactiva.

**Limitación aceptada y documentada:** el unique constraint `(condominio_id, torre, piso, numero)` no distingue por `activa`. Mientras una unidad desactivada mantenga su dirección, no se puede crear una fila nueva con esa misma dirección — hay que reactivar la fila existente. Un índice funcional Oracle (único solo sobre filas `activa=true`) resolvería esto, pero es complejidad adicional sin caso de uso real hoy; queda como techo conocido, no se construye.

## 5. Eventos Outbox: ninguno para `Unidad`

`_registrar_evento` en `condominio_repository.py` ya trata `tipo_evento` como opcional — `Condominio` lo usa por su propio caso de uso documentado, no porque el `AGENTS.md` exija eventos para todo agregado. Sin consumidor real para `Unidad`, se omite (YAGNI, §6 Ponytail). No se modifica `app/model/outbox.py`, `app/events/outbox_event.py` ni `CondominioRepository`.

## 6. Manejo de errores

- `UnidadNoEncontradaException` → 404 (mismo patrón que `CondominioNoEncontradoException`).
- `UnidadDuplicadaException` → 409, lanzada **solo** cuando `IntegrityError.orig` contiene `"ORA-00001"` (unique constraint de Oracle). Cualquier otro `IntegrityError` (ej. `ORA-02291`, FK rota) se re-lanza sin traducir — no se oculta como un 409 falso.

## 7. Dependencias y contrato para la etapa 2 (`ms-usuario`)

- `GET /condominios/{id_condominio}/unidades/{id_unidad}` → `{id, condominio_id, torre, piso, numero, activa}` o 404 — para validar una asociación antes de crearla.
- `GET /condominios/{id_condominio}/unidades` → listado, para selector en el panel admin.
- **Pendiente explícito, no resuelto acá:** `ms-gastos-comunes`/`ms-espacios-comunes` no validan su `unidadId`/`condominio_id` contra este catálogo. Cómo se propaga el rol-por-condominio al JWT/BFF (hoy el rol es global) es la pregunta central del diseño de `ms-usuario`, no de este sub-proyecto.
- El riesgo de suplantación de la sección 3 también aplica a cualquier llamada que `ms-usuario` haga hacia este servicio — a tener en cuenta en ese diseño.

## 8. Fuera de alcance, confirmado explícitamente

No se modifica `ms-gastos-comunes`, `ms-espacios-comunes`, BFF, frontends, ni el mecanismo de autorización de `ms-condominios`. No se verificó la tarjeta Trello #46 en vivo (sin herramienta MCP de Trello disponible en esta sesión) — lo documentado acá sobre su estado viene de `ms-condominios/AGENTS.md` §1, no de una consulta directa al board.

## 9. Riesgo heredado y pendiente explícito para `ms-usuario` (addendum, 2026-10-15)

Dejado por escrito a pedido explícito, sin implementar ninguna solución — es trabajo de diseño para la etapa 2, no de este sub-proyecto.

**Riesgo de suplantación vía `X-Usuario-Roles` (ya documentado en §3, reforzado acá tras la revisión independiente):** `app/middleware/auth_roles.py:requiere_roles` confía ciegamente en el header `X-Usuario-Roles`, sin ninguna verificación criptográfica — a diferencia de `ms-gastos-comunes`, que valida el JWT por su cuenta y solo *loguea* si el header del BFF no coincide, nunca confía en él para autorizar. Cualquier cliente con acceso directo al puerto de `ms-condominios` (sin pasar por el BFF) puede fijar `X-Usuario-Roles: ADMIN` y operar como administrador sobre `Condominio` y `Unidad` por igual. Verificado en esta sesión: en local, `docker-compose.yml` expone el puerto 8084 directo al host; en prod, `terraform-cloud/` todavía no define un servicio ECS para `ms-condominios`, así que la mitigación ("nunca expuesto sin pasar por el BFF") es una intención escrita, no algo que la infraestructura esté forzando hoy. Los endpoints de `Unidad` usan exactamente el mismo mecanismo — no agravan el riesgo, pero tampoco lo corrigen.

**Incompatibilidad real entre "todo ADMIN-only" y lo que `ms-usuario` va a necesitar:** los 5 endpoints de `Unidad` son ADMIN-only (§3) porque hoy no existe ninguna forma de validar "esta es la unidad propia del residente". Cuando `ms-usuario` exista, aparecen al menos dos preguntas que este sub-proyecto no resuelve y que la etapa 2 debe responder explícitamente, no heredar por default:

1. **¿Cómo llama `ms-usuario` a estos endpoints?** Si lo hace vía el BFF con el mismo header `X-Usuario-Roles`, necesita presentarse como `ADMIN` aunque esté actuando en nombre de un residente que se está registrando — eso amplía quién puede fijar ese header de facto. Si en cambio `ms-usuario` llama directo a `ms-condominios` (service-to-service, sin pasar por el BFF), hereda el mismo problema de exposición de red de arriba, ahora con un cliente más.
2. **¿Quién valida "unidad propia"?** Hoy nadie lo hace — ni `ms-condominios` (no tiene el concepto de "residente de esta unidad"), ni el BFF (los roles son globales, no por condominio ni por unidad). Si `ms-usuario` asume que puede confiar en `GET /unidades/{id}` para eso, se equivoca: ese endpoint es ADMIN-only y no filtra por ownership, porque ese ownership todavía no existe en ningún lado del sistema.

Ninguna de las dos preguntas tiene una respuesta implementada en este sub-proyecto. Quedan como insumo obligatorio para el diseño de `ms-usuario`, no como deuda técnica de `Unidad` en sí.
