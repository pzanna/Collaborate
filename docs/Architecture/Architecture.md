# Eunice Research Platform - Solution Architecture

## Architecture Overview

The Eunice research platform, named after the AI from the William Gibson novel [Agency](<https://en.wikipedia.org/wiki/Agency_(novel)>), is designed to facilitate advanced research workflows by integrating various tools and services. Its architecture is based on a microservices approach, allowing for flexibility, scalability, and ease of maintenance.

![Architecture Diagram](Logical_Design.jpeg)

The Eunice platform organises research work in a hierarchical structure:

**Project → Research Topic → Plan → Tasks**

This structure allows for better organisation, clearer separation of concerns, and more intuitive navigation.

Refer to the [Hierarchical Research Structure](HIERARCHICAL_RESEARCH_STRUCTURE.md) for detailed information on how research is organised within the platform.

## Key Components

### Web Interface

The web interface serves as the primary user interface for researchers, providing access to the platform's features and functionalities. It is built using React and provides a user-friendly experience for managing research projects, accessing data, and collaborating with the team.

### API Gateway

The API Gateway acts as a single entry point for all client requests, routing them to the appropriate microservices and handling authentication, authorisation, and rate limiting.
It also implements security measures such as encryption, authentication, and authorisation to protect sensitive data and ensure secure communication between services.

### MCP Server

The MCP (Microservices Control Plane) server is the core component of the Eunice platform, responsible for managing the microservices architecture and coordinating expert consultations. It provides the following functionalities:

- **Service Discovery**: Automatically detects and registers microservices, allowing them to communicate with each other seamlessly.

- **Load Balancing**: Distributes incoming requests across multiple instances of microservices to ensure optimal performance and reliability.

- **Monitoring and Logging**: Collects metrics, logs, and traces from microservices to provide insights into system performance, health, and usage patterns.

- **Configuration Management**: Centralises configuration settings for microservices, allowing for dynamic updates without requiring service restarts.

- **Real-time Communication**: Provides WebSocket-based communication for live updates and expert consultations.

### Agents

The platform features specialised agent personas that provide expert consultations through the MCP server:

#### Researcher Manager

The [Researcher Manager](Research_Manager.md) oversees the operational aspects of the research projects, including agent coordination, resource management and usage costs. It also supports the user in strategic planning, project management, and ensuring a project's efficient execution while fostering interdisciplinary collaboration.

#### Memory Agent

Utilises a local knowledge base for storing research data, documents, and findings.

#### Literature Agent

Leverages multiple search engines and academic databases for comprehensive information gathering, including:

- Multi-engine web search (Google, Bing, Yahoo)
- Semantic Scholar API integration for academic papers
- Google Scholar fallback for scholarly content
- Advanced content extraction and analysis
- High-level research workflows for automated data collection
- Multi-source fact verification capabilities

#### Executor Agent

Handles code execution, API calls, data processing, and file operations for the research system.

#### Planning Agent

Handles planning, analysis, reasoning, and synthesis tasks for the research system.

#### AI Agent

The Eunice platform leverages various AI models to enhance its research capabilities including models from OpenAI, xAI, Anthopic, and other locally hosted models. These models are used for natural language processing, data analysis, and other AI-driven tasks to support the research process. LLMs (Large Language Models) are accessed by API calls to ensure scalability and flexibility in model version and cost.

### Personas

- **Neurobiologist**: Leads biological aspects of neuron interfacing, including brain mapping, neuron extraction/isolation, viability assessments, and culture maintenance. Provides expert guidance on experimental design to ensure ethical and effective biological system integration. Refer to the [Neurobiologist Persona](Personas/01_Neurobiologist.md) for more details.

- **Computational Neuroscientist**: Bridges biology and computing by modeling neural activity and designing protocols to interface neurons with digital systems. Specialises in bio-digital communication protocols and neural signal processing. Refer to the [Computational Neuroscientist Persona](Personas/02_Computational_Neuroscientist.md) for more details.

- **AI/ML Engineer & Data Scientist**: Builds and trains artificial neural networks as benchmarks for comparison, integrates them with biological interfaces, and analyzes experimental data using statistical methods to validate performance outcomes. Refer to the [AI/ML Engineer & Data Scientist Persona](Personas/05_AI_ML_Engineer_Data_Scientist.md) for more details.

- **Biomedical Systems Engineer**: Develops hardware/software interfaces between biological and digital systems, ensuring proper signal acquisition, processing, and system integration. Specialises in bio-digital hybrid systems, including sensor integration and data acquisition. Refer to the [Biomedical Systems Engineer Persona](Personas/03_Biomedical_Systems_Engineer.md) for more details.

- **Animal Biologist & Bioethics Specialist**: Oversees animal welfare for research subjects while advising on ethical implications of bio-digital interfacing, securing regulatory approvals, and ensuring compliance with biosafety and data privacy standards. Refer to the [Animal Biologist & Bioethics Specialist Persona](Personas/04_Animal_Biologist_Bioethics_Specialist.md) for more details.

- **Microbiologist**: Focuses on microbial aspects of neuron culturing and interfacing experiments, ensuring sterility, preventing contamination, and optimizing culture conditions to maintain neuron viability in bio-digital systems. Refer to the [Microbiologist Persona](Personas/06_Microbiologist.md) for more details.

- **Technical/Scientific Writer**: Documents research methodologies, findings, and comparisons between biological neurons and ANNs; prepares manuscripts for publication, grant proposals, and reports; ensures clear, accurate communication of complex technical concepts to diverse audiences. Refer to the [Technical/Scientific Writer Persona](Personas/07_Technical_Scientific_Writer.md) for more details.

#### Persona Consultation System

The persona system provides real-time expert consultations through the MCP protocol:

- **Expert Routing**: Automatically routes consultation requests to appropriate domain experts
- **Multi-Modal Queries**: Supports text-based queries with contextual information
- **Confidence Scoring**: Provides AI-generated confidence metrics for consultation quality
- **Persistent History**: Maintains consultation history for research continuity
- **Real-time Responses**: WebSocket-based communication for immediate expert feedback

```python
# Example consultation request
consultation_response = await mcp_client.request_persona_consultation(
    expertise_area="neuron_preparation",
    query="What are optimal buffer conditions for hippocampal neuron isolation?",
    context={
        "experiment_type": "patch_clamp",
        "animal_model": "rat",
        "age": "P14-P21"
    },
    preferred_persona="neurobiologist"
)
```

#### Integration Architecture

The persona system integrates with the MCP server through:

- **PersonaMCPIntegration**: Main integration layer managing persona lifecycle
- **PersonaRegistry**: Manages persona agent registration and capabilities
- **ConsultationHistory**: Persistent storage of all expert interactions
- **CapabilityMapping**: Routes expertise areas to appropriate persona agents

_Refer to the [Persona System Documentation](Personas/README.md) for more details._

### Data Storage

The Eunice platform uses a combination of databases for structured and unstructured data storage:

- **SQLite**: For structured data, including user accounts, project metadata, and task management.
- **Memory Cache**: For caching frequently accessed data to improve performance.
- **File Storage**: For unstructured data such as documents, images, and other research artifacts.
- **Knowledge Base**: A local knowledge base for storing research data, documents, and findings, which is utilised by the Memory Agent.
- **Literature Database**: A specialised database for storing literature search results, including metadata and content from academic papers and articles.
