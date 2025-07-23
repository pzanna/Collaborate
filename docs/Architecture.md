# Eunice Research Platform - Solution Architecture Documentation

## Architecture Overview

The Eunice research platform, named after the AI from the William Gibson novel [Agency](<https://en.wikipedia.org/wiki/Agency_(novel)>), is designed to facilitate advanced research workflows by integrating various tools and services. Its architecture is based on a microservices approach, allowing for flexibility, scalability, and ease of maintenance.

![Architecture Diagram](Architecture.jpeg)

## Key Components

## Web Interface

The web interface serves as the primary user interface for researchers, providing access to the platform's features and functionalities. It is built using React and provides a user-friendly experience for managing research projects, accessing data, and collaborating with the team.

## API Gateway

The API Gateway acts as a single entry point for all client requests, routing them to the appropriate microservices and handling authentication, authorization, and rate limiting.
It also implements security measures such as encryption, authentication, and authorization to protect sensitive data and ensure secure communication between services.

## MCP Server

The MCP (Microservices Control Plane) server is the core component of the Eunice platform, responsible for managing the microservices architecture and coordinating expert consultations. It provides the following functionalities:

- **Service Discovery**: Automatically detects and registers microservices, allowing them to communicate with each other seamlessly.

- **Load Balancing**: Distributes incoming requests across multiple instances of microservices to ensure optimal performance and reliability.

- **Monitoring and Logging**: Collects metrics, logs, and traces from microservices to provide insights into system performance, health, and usage patterns.

- **Configuration Management**: Centralizes configuration settings for microservices, allowing for dynamic updates without requiring service restarts.

- **Persona Integration**: Manages expert consultation requests and routes them to appropriate specialized persona agents.

- **Real-time Communication**: Provides WebSocket-based communication for live updates and expert consultations.

## Researcher Manager

The [Researcher Manager](Research_Manager.md) oversees the operational aspects of the research projects, including agent coordination, resource management and usage costs. It also supports the user in strategic planning, project management, and ensuring a project's efficient execution while fostering interdisciplinary collaboration.

## Agent Personas

The platform features specialized agent personas that provide expert consultations through the MCP server:

### Core Persona Agents

- **Neurobiologist**: Leads biological aspects of neuron interfacing, including brain mapping, neuron extraction/isolation, viability assessments, and culture maintenance. Provides expert guidance on experimental design to ensure ethical and effective biological system integration.

- **Computational Neuroscientist**: Bridges biology and computing by modeling neural activity and designing protocols to interface neurons with digital systems. Specializes in bio-digital communication protocols and neural signal processing.

- **AI/ML Engineer & Data Scientist**: Builds and trains artificial neural networks as benchmarks for comparison, integrates them with biological interfaces, and analyzes experimental data using statistical methods to validate performance outcomes.

- **Biomedical Systems Engineer**: Develops hardware/software interfaces between biological and digital systems, ensuring proper signal acquisition, processing, and system integration.

- **Animal Biologist & Bioethics Specialist**: Oversees animal welfare for research subjects while advising on ethical implications of bio-digital interfacing, securing regulatory approvals, and ensuring compliance with biosafety and data privacy standards.

- **Technical/Scientific Writer**: Documents research methodologies, findings, and comparisons between biological neurons and ANNs; prepares manuscripts for publication, grant proposals, and reports; ensures clear, accurate communication of complex technical concepts to diverse audiences.

### Persona Consultation System

The persona system provides real-time expert consultations through the MCP protocol:

- **Expert Routing**: Automatically routes consultation requests to appropriate domain experts
- **Multi-Modal Queries**: Supports text-based queries with contextual information
- **Confidence Scoring**: Provides AI-generated confidence metrics for consultation quality
- **Persistent History**: Maintains consultation history for research continuity
- **Real-time Responses**: WebSocket-based communication for immediate expert feedback

### Consultation Protocol

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

### Integration Architecture

The persona system integrates with the MCP server through:

- **PersonaMCPIntegration**: Main integration layer managing persona lifecycle
- **PersonaRegistry**: Manages persona agent registration and capabilities
- **ConsultationHistory**: Persistent storage of all expert interactions
- **CapabilityMapping**: Routes expertise areas to appropriate persona agents

_Refer to the [Persona System Documentation](Personas/README.md) for more details._

## Project Structure

The Eunice platform organizes research work in a hierarchical structure:
**Project → Research Topic → Plan → Tasks**
This structure allows for better organization, clearer separation of concerns, and more intuitive navigation.

Refer to the [Hierarchical Research Structure](HIERARCHICAL_RESEARCH_STRUCTURE.md) for detailed information on how research is organized within the platform.

## Tooling and Services

The Eunice platform integrates various tools and services to support its research activities:

- **Memory**: Utilises a local knowledge base for storing research data, documents, and findings.

- **Retriever**: Leverages the Internet for gathering information, literature reviews, research papers and staying updated with the latest research in neuroscience and AI.

- **Executor**: Handles code execution, API calls, data processing, and file operations for the research system.

- **Planning**: Handles planning, analysis, reasoning, and synthesis tasks for the research system.

## AI Models

The Eunice platform leverages various AI models to enhance its research capabilities including models from OpenAI, xAI, Anthopic, and other locally hosted models. These models are used for natural language processing, data analysis, and other AI-driven tasks to support the research process. LLMs (Large Language Models) are accessed by API calls to ensure scalability and flexibility in model version and cost.
