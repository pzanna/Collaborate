# Research Team Personas - Index

This directory contains individual persona files for each research team role in the cerebral neuron research project, along with documentation for the integrated persona consultation system.

## Overview

The research team consists of interdisciplinary experts combining biology, neuroscience, engineering, AI, compliance, and communication expertise. Each role is designed to support the project's goal of interfacing biological neurons with computer systems and comparing their performance to artificial neural networks.

## 🧠 Persona Consultation System

The Eunice platform provides an advanced persona consultation system that allows researchers to request expert advice from specialized AI personas through the MCP (Message Control Protocol) server.

### Key Features

- **Real-time Consultations**: WebSocket-based communication for immediate expert responses
- **Expert Routing**: Automatic routing to appropriate domain specialists
- **Multi-Modal Queries**: Support for complex queries with contextual information
- **Confidence Scoring**: AI-generated confidence metrics for consultation quality
- **Persistent History**: Complete consultation tracking for research continuity
- **Capability Discovery**: Dynamic discovery of available expertise areas

### Consultation Protocol

```python
# Request expert consultation
consultation_response = await mcp_client.request_persona_consultation(
    expertise_area="neuron_preparation",
    query="What are optimal conditions for maintaining hippocampal neurons in culture for LTP experiments?",
    context={
        "experiment_type": "LTP",
        "neuron_type": "hippocampal",
        "culture_duration": "21+ days"
    },
    preferred_persona="neurobiologist"
)

# Get available personas and capabilities
capabilities = await mcp_client.get_persona_capabilities()

# Review consultation history
history = await mcp_client.get_persona_history(limit=10)
```

### System Architecture

The persona system integrates with the platform through:

- **MCP Server Integration**: Handles consultation requests and routing
- **Persona Registry**: Manages available personas and their capabilities
- **Consultation History**: Persistent storage of all expert interactions
- **Real-time Communication**: WebSocket-based consultation delivery

## Team Structure

The roles are categorized into **Project Management**, **Scientific/Technical Experts**, **Engineering and Development**, **Support and Compliance**, and **Communication and Documentation**.

## Individual Role Files

### Project Management

- [**Research Manager**](./01_Research_Manager.md) - Project coordination, resource management, and strategic planning

### Scientific/Technical Experts

- [**Neurobiologist**](./02_Neurobiologist.md) - Neuron preparation, maintenance, and bio-computer interfacing
- [**Computational Neuroscientist**](./03_Computational_Neuroscientist.md) - Neural modeling and bio-digital protocol design
- [**Biomedical Systems Engineer**](./04_Biomedical_Systems_Engineer.md) - Hardware/software interface development

### Engineering and Development

- [**AI/ML Engineer & Data Scientist**](./05_AI_ML_Engineer_Data_Scientist.md) - ANN development and data analysis

### Support and Compliance

- [**Animal Biologist & Bioethics Specialist**](./06_Animal_Biologist_Bioethics_Specialist.md) - Animal welfare and ethical compliance

### Communication and Documentation

- [**Technical/Scientific Writer**](./07_Technical_Scientific_Writer.md) - Documentation and publication preparation

## Team Composition Notes

This structure assumes a lean initial team of 6-8 members, leveraging existing lab technicians for operational support. Priority should be given to hiring the Neurobiologist, Biomedical Systems Engineer, and AI/ML Engineer & Data Scientist for the proof-of-concept phase.

## File Structure

Each persona file contains:

- **Job Description**: Core role overview
- **Key Responsibilities**: Specific tasks and duties
- **Required Qualifications**: Education and experience requirements
- **Required Knowledge**: Technical and domain expertise needed
- **Why Critical**: Rationale for the role's importance to the project
- **AI System Prompt**: Detailed prompt for configuring AI agents to simulate or assist in this role

## Consultation Capabilities

Each persona provides specialized consultation capabilities accessible through the MCP server:

- **Domain Expertise**: Deep knowledge in specific research areas
- **Contextual Understanding**: Ability to provide advice based on experimental context
- **Cross-disciplinary Integration**: Knowledge of how different domains interact
- **Practical Guidance**: Actionable advice for experimental design and execution
- **Risk Assessment**: Identification of potential issues and mitigation strategies

## Testing the Persona System

To test the persona consultation system:

```bash
# Start the MCP server
python mcp_server.py

# Run the persona system test client
python tests/test_mcp_persona_client.py
```

This will demonstrate:

- Persona capability discovery
- Expert consultation requests
- Consultation history tracking
- Error handling for unknown expertise areas

## Usage

These persona files can be used for:

- Hiring and recruitment planning
- Role definition and clarity
- Team coordination and communication
- AI agent configuration for simulation or assistance
- Training and onboarding new team members
