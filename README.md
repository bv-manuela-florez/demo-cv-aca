# 🚀 Multi-Agent Endpoint Async

Este proyecto implementa una API asíncrona con FastAPI para orquestar agentes inteligentes desplegados en Azure AI Projects. Permite enrutar mensajes de usuario a diferentes agentes según la clasificación automática y gestionar hilos de conversación.

---

## 🏗️ Estructura del Proyecto

```
democv-foundry-multiagent-endpoint-async/
│
├── main.py                      # API principal FastAPI, lógica de orquestación de agentes
├── utils/
│   ├── chat_history_models.py   # Modelos Pydantic para historial de chat y lógica de guardado en Cosmos DB
│   ├── cosmos_utils_orm.py      # Utilidades ORM para Cosmos DB
│   ├── keyvault.py              # Utilidades para Azure Key Vault
│   └── telemetry.py             # Utilidades para telemetría y logging
├── requirements.txt             # Dependencias Python
├── .env                         # Variables de entorno (Azure, agentes)
└── README.md                    # Este archivo
```

---

## 💡 ¿Qué hace este proyecto?

- Expone un endpoint `/run-agent/` para recibir mensajes y enrutar a agentes inteligentes.
- Utiliza Azure AI Projects para gestionar agentes y sus hilos de conversación.
- Clasifica el mensaje usando un agente selector y redirige a agentes especializados (FAQ, Estado de Caso).
- Responde de forma limpia, eliminando referencias técnicas y metadatos de la respuesta.

---

## 💾 Guardado de interacciones en Azure Cosmos DB

- Cada interacción entre usuario y agente se guarda automáticamente en Cosmos DB.
- El modelo `ConversationChat` (en `utils/chat_history_models.py`) estructura la sesión, incluyendo el mensaje del usuario, la respuesta del agente, uso de tokens, herramientas usadas, y metadatos de tiempo.
- El guardado se realiza desde `main.py` usando los modelos definidos en `utils/chat_history_models.py`.

**Ejemplo de flujo de guardado:**
1. El usuario envía un mensaje al endpoint `/run-agent/`.
2. El sistema orquesta la consulta y obtiene la respuesta del agente.
3. Se construyen los modelos de historial de chat y se guarda la interacción en Cosmos DB.

---

## ⚙️ Instalación y Ejecución

1. **Clona el repositorio:**
    ```bash
    git clone <repo-url>
    cd democv-foundry-multiagent-endpoint-async
    ```

2. **Instala dependencias:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # o venv\Scripts\activate en Windows
    pip install -r requirements.txt
    ```

3. **Configura tu archivo `.env`:**
    - AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
    - AIProjectEndpoint, SELECTOR_AGENT_ID, RAG_AGENT_ID, CASE_AGENT_ID

4. **Ejecuta la API:**
    ```bash
    uvicorn main:app --reload
    ```

---

## 🔗 Endpoint principal

- **POST `/run-agent/`**
    - Recibe: `agentid`, `message`, `threadId` (opcional)
    - Orquesta agentes y responde según la clasificación automática.

---

## 🧠 Lógica de agentes

- El agente selector clasifica el mensaje.
- Según la clasificación, se redirige al agente FAQ o Estado de Caso.
- Las respuestas se limpian para eliminar metadatos y referencias técnicas.

---

## ☁️ Azure Integration

- Autenticación y gestión de agentes usando Azure Identity y Azure AI Projects SDK.
- Variables de entorno para credenciales y endpoints.

---

## 👤 Autor

**Manuela BigView SAS**

---

## 📜 Licencia

Licencia privada BigView SAS.
Contacto: `legal@bigview.ai`
