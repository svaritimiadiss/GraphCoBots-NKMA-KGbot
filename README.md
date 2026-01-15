# GraphCoBots-NKMA-KGbot

**GraphCoBots-NKMA-KGbot** is a Knowledge Graph–driven conversational AI chatbot that provides structured, research-oriented information about **selected artefacts of the Nikos Kazantzakis Museum (Crete, Greece)**. The system forms part of the broader **GraphCoBots** research framework, which investigates distributed, collaborative, and Knowledge Graph-based multi-chatbot systems for museums and cultural heritage organizations.

The chatbot is designed to support natural language access to artefact-level cultural heritage information by combining semantic data modeling with conversational interaction mechanisms.

---

## Research Context

This repository constitutes a research artifact addressing the following themes:

* Knowledge Graph modeling for museum artefacts
* Conversational AI for cultural heritage interpretation
* Semantic enrichment of museum collections
* Distributed and collaborative chatbot architectures

The system supports experimental evaluation and reproducibility in academic research related to digital cultural heritage and human–computer interaction.

---

## Repository Structure

```
.
├── actions/                # GitHub Actions workflows
├── data/                   # Knowledge Graph data and structured exports
├── scripts/                # Utility and helper scripts
├── config.yml              # Chatbot configuration
├── domain.yml              # Conversational domain (intents, entities, responses)
├── endpoints.yml           # External service endpoints
├── credentials.yml         # Credentials file (user-provided, not committed)
├── docker-compose.yml      # Docker Compose deployment
├── Dockerfile              # Docker image definition
├── index.html              # Web interface or embedded UI
├── server.sh               # Startup script
├── LICENSE                 # Apache License 2.0 (source code)
├── LICENSE-DATA            # CC BY 4.0 (data & Knowledge Graphs)
└── README.md               # Project documentation
```

---

## Prerequisites

To deploy and run the chatbot, the following are required:

* Docker and Docker Compose (**recommended for reproducibility**), or
* Python 3.x for local execution
* Valid credentials for any external services, provided via `credentials.yml`

---

## Configuration

### `config.yml`

Defines general runtime parameters, including ports, logging levels, and operational settings.

### `domain.yml`

Specifies the conversational domain, including intents, entities, and response templates related to museum artefacts.

### `endpoints.yml`

Configures external API endpoints and service integrations.

### `credentials.yml`

Stores sensitive information such as API keys or access tokens. This file must be created by the user and **must not be committed** to the repository.

---

## Running the Chatbot

### Option 1: Docker (Recommended)

```bash
docker compose up --build
```

This command builds and launches the chatbot in a containerized environment, enabling portable and reproducible deployment.

---

### Option 2: Local Execution

1. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the chatbot service:

```bash
./server.sh
```

---

## Knowledge Graph Usage

The chatbot is backed by a **Knowledge Graph** that semantically represents selected artefacts of the Nikos Kazantzakis Museum, including descriptive, contextual, and relational information. For transparency and reproducibility, Knowledge Graph content is provided using declarative and portable formats such as:

* Cypher scripts (`.cypher` files)
* CSV files suitable for Neo4j import

Binary database files are intentionally excluded from the repository.

---

## Licensing

This repository follows a **dual-license model**:

* **Source code**: Apache License 2.0 (see `LICENSE`)
* **Data, Knowledge Graphs, and metadata**: Creative Commons Attribution 4.0 International (CC BY 4.0) (see `LICENSE-DATA`)

Users are responsible for complying with the appropriate license depending on the material reused.

---

## Citation

If you use this software or its associated data in academic research, please cite the relevant **GraphCoBots** publications. A `CITATION.cff` file may be added to facilitate automated citation workflows.

---

## Notes for Researchers and Developers

* Do not commit credentials or secrets
* Use Docker to ensure reproducible experiments
* Version Knowledge Graph updates using `.cypher` or CSV files
* Avoid committing large binaries or database directories

---

## Contact

For research-related questions, collaboration opportunities, or technical support, please contact the repository owner via GitHub.

---

## Acknowledgements

This work contributes to ongoing research on conversational AI and Knowledge Graphs for cultural heritage applications, with a focus on museum artefact interpretation and intelligent visitor engagement.
