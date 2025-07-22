# Persona System Quick Start Guide

## Overview

The Eunice Persona System provides real-time access to specialized AI experts through the MCP server. This guide will help you get started with requesting expert consultations.

## Prerequisites

### 1. Start the MCP Server

```bash
# Start the MCP server with persona integration
python mcp_server.py
```

### 2. Configure AI API Keys

Ensure you have API keys configured for the AI services:

```bash
# In your .env file or environment
export OPENAI_API_KEY="your_openai_key"
export XAI_API_KEY="your_xai_key"
```

### 3. Test the System

```bash
# Run the persona system test
python tests/test_mcp_persona_client.py
```

## Basic Usage

### Connect to MCP Server

```python
from src.mcp.client import MCPClient

# Initialize and connect
mcp_client = MCPClient(host="127.0.0.1", port=9000)
await mcp_client.connect()
```

### Discover Available Personas

```python
# Get all available personas and their capabilities
capabilities = await mcp_client.get_persona_capabilities()

print("Available personas:")
for persona_name, info in capabilities['available_personas'].items():
    print(f"- {persona_name}: {info['capabilities']}")
```

### Request Expert Consultation

```python
# Request neurobiologist advice
consultation = await mcp_client.request_persona_consultation(
    expertise_area="neuron_preparation",
    query="What are optimal conditions for hippocampal neuron isolation?",
    context={
        "animal_model": "rat",
        "age": "P14-P21",
        "experiment_type": "patch_clamp"
    },
    preferred_persona="neurobiologist"
)

print(f"Expert Response: {consultation['expert_response']}")
print(f"Confidence: {consultation['confidence']}%")
print(f"Persona: {consultation['persona_type']}")
```

### Review Consultation History

```python
# Get recent consultation history
history = await mcp_client.get_persona_history(limit=5)

for consultation in history['consultations']:
    print(f"Query: {consultation['query'][:50]}...")
    print(f"Expert: {consultation['persona_type']}")
    print(f"Status: {consultation['status']}")
    print("---")
```

## Common Expertise Areas

### Neurobiologist

- `neuron_preparation` - Cell isolation and preparation
- `cell_culture` - Culture maintenance and optimization
- `electrophysiology` - Recording techniques
- `brain_mapping` - Circuit identification
- `synaptic_plasticity` - LTP/LTD protocols

### Computational Neuroscientist

- `neural_modeling` - Mathematical models
- `signal_processing` - Neural signal analysis
- `bio_digital_interface` - Bio-digital protocols
- `data_analysis` - Experimental data interpretation

### AI/ML Engineer & Data Scientist

- `artificial_neural_networks` - ANN development
- `machine_learning` - ML optimization
- `data_analysis` - Statistical analysis
- `model_validation` - Performance evaluation

### Biomedical Systems Engineer

- `hardware_interface` - Bio-electronic interfaces
- `signal_acquisition` - Data acquisition
- `system_integration` - Hardware/software integration
- `instrumentation` - Measurement systems

### Animal Biologist & Bioethics Specialist

- `animal_welfare` - Ethical practices
- `regulatory_compliance` - IACUC requirements
- `biosafety` - Laboratory safety
- `ethics_review` - Research ethics

### Technical/Scientific Writer

- `manuscript_preparation` - Scientific writing
- `grant_writing` - Funding proposals
- `documentation` - Technical docs
- `communication` - Science communication

## Best Practices

### 1. Provide Context

Always include relevant experimental context:

```python
context = {
    "experiment_type": "patch_clamp",
    "animal_model": "mouse",
    "age": "P21",
    "brain_region": "hippocampus",
    "recording_type": "whole_cell"
}
```

### 2. Be Specific with Queries

Instead of: "How do I record from neurons?"
Use: "What are optimal pipette resistance and seal criteria for whole-cell patch-clamp recordings from hippocampal CA1 pyramidal neurons?"

### 3. Use Appropriate Expertise Areas

Match your query to the most relevant expertise area:

- Technical procedures → specific expertise areas
- General advice → broader areas like "data_analysis"
- Ethical concerns → "animal_welfare" or "ethics_review"

### 4. Handle Errors Gracefully

```python
try:
    consultation = await mcp_client.request_persona_consultation(
        expertise_area="unknown_area",
        query="Test query"
    )
except Exception as e:
    print(f"Consultation failed: {e}")
    # Handle error appropriately
```

## Example Workflows

### Experimental Design

```python
# Get advice on experimental design
design_consultation = await mcp_client.request_persona_consultation(
    expertise_area="electrophysiology",
    query="What are optimal recording parameters for measuring synaptic transmission in hippocampal slices?",
    context={
        "slice_thickness": "300um",
        "temperature": "32C",
        "perfusion_rate": "2ml/min",
        "experiment_duration": "2-3 hours"
    },
    preferred_persona="neurobiologist"
)
```

### Protocol Optimization

```python
# Optimize existing protocols
optimization = await mcp_client.request_persona_consultation(
    expertise_area="cell_culture",
    query="How can I improve neuron survival in long-term hippocampal cultures?",
    context={
        "current_survival": "70% at 14 days",
        "culture_medium": "Neurobasal + B27",
        "plating_density": "50k cells/well",
        "coating": "poly-L-lysine + laminin"
    },
    preferred_persona="neurobiologist"
)
```

### Data Analysis

```python
# Get analysis advice
analysis = await mcp_client.request_persona_consultation(
    expertise_area="data_analysis",
    query="What statistical tests should I use for comparing synaptic strength between groups?",
    context={
        "data_type": "EPSC amplitudes",
        "groups": 3,
        "n_per_group": 8,
        "distribution": "not_normal",
        "repeated_measures": True
    },
    preferred_persona="ai_ml_engineer"
)
```

## Troubleshooting

### Common Issues

1. **Connection Failed**

   - Ensure MCP server is running
   - Check host/port configuration
   - Verify network connectivity

2. **Persona Not Available**

   - Check persona system initialization
   - Verify AI API keys are configured
   - Review MCP server logs

3. **Low Confidence Responses**
   - Provide more specific context
   - Use appropriate expertise area
   - Rephrase query for clarity

### Debug Commands

```bash
# Check MCP server status
curl -X GET http://localhost:9000/health

# View logs
tail -f logs/mcp_server.log

# Test persona system
python tests/test_mcp_persona_client.py
```

## Next Steps

1. **Explore Advanced Features**: Multi-modal consultations, collaboration between personas
2. **Integration**: Embed persona consultations in your research workflows
3. **Customization**: Develop custom personas for specialized domains
4. **Automation**: Create automated consultation pipelines for common queries

For detailed technical documentation, see [MCP Persona System Documentation](../docs/MCP_Persona_System.md).
