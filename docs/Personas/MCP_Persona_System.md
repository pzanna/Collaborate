# MCP Persona System Documentation

## Overview

The MCP (Message Control Protocol) Persona System is an advanced expert consultation framework that integrates specialized AI personas with the Eunice research platform. It provides real-time access to domain-specific expertise through a standardized protocol.

## Architecture

### Core Components

#### 1. PersonaMCPIntegration

The main integration layer that manages persona lifecycle and consultation routing.

**Location**: `src/personas/mcp_integration.py`

**Responsibilities**:

- Initialize and manage persona agents
- Handle consultation requests from MCP server
- Coordinate responses between personas and clients
- Maintain consultation history and statistics

#### 2. PersonaRegistry

Manages the registration and capabilities of available persona agents.

**Location**: `src/personas/persona_registry.py`

**Responsibilities**:

- Register and track available personas
- Map expertise areas to appropriate personas
- Manage persona lifecycle (initialization, health checks)
- Provide capability discovery for clients

#### 3. MCP Server Integration

Extends the MCP server with persona consultation endpoints.

**Location**: `src/mcp/server.py`

**New Message Types**:

- `persona_consultation_request` - Request expert consultation
- `get_persona_capabilities` - Discover available personas
- `get_persona_history` - Retrieve consultation history

## Consultation Protocol

### Request Structure

```python
@dataclass
class PersonaConsultationRequest:
    request_id: str
    expertise_area: str
    query: str
    context: Dict[str, Any] = field(default_factory=dict)
    preferred_persona: Optional[str] = None
    priority: str = "normal"
    created_at: datetime = field(default_factory=datetime.now)
```

### Response Structure

```python
@dataclass
class PersonaConsultationResponse:
    request_id: str
    persona_type: str
    status: str
    expert_response: Optional[str] = None
    confidence: Optional[float] = None
    error: Optional[str] = None
    completed_at: datetime = field(default_factory=datetime.now)
```

## Available Personas

### 1. Neurobiologist

**Expertise Areas**:

- `neuron_preparation` - Cell isolation and preparation techniques
- `cell_culture` - Neuron culture maintenance and optimization
- `electrophysiology` - Patch-clamp and recording techniques
- `brain_mapping` - Neural circuit identification and mapping
- `synaptic_plasticity` - LTP/LTD experimental protocols

**Example Query**:

```python
consultation = await mcp_client.request_persona_consultation(
    expertise_area="neuron_preparation",
    query="What are optimal buffer conditions for hippocampal neuron isolation?",
    context={
        "animal_model": "rat",
        "age": "P14-P21",
        "experiment_type": "patch_clamp"
    },
    preferred_persona="neurobiologist"
)
```

### 2. Computational Neuroscientist

**Expertise Areas**:

- `neural_modeling` - Mathematical models of neural systems
- `signal_processing` - Neural signal analysis and filtering
- `bio_digital_interface` - Protocol design for bio-digital communication
- `data_analysis` - Experimental data interpretation

### 3. AI/ML Engineer & Data Scientist

**Expertise Areas**:

- `artificial_neural_networks` - ANN architecture and training
- `machine_learning` - ML algorithm selection and optimization
- `data_analysis` - Statistical analysis and visualization
- `model_validation` - Performance metrics and evaluation

### 4. Biomedical Systems Engineer

**Expertise Areas**:

- `hardware_interface` - Bio-electronic interface design
- `signal_acquisition` - Data acquisition system setup
- `system_integration` - Hardware/software integration
- `instrumentation` - Measurement system design

### 5. Animal Biologist & Bioethics Specialist

**Expertise Areas**:

- `animal_welfare` - Ethical animal research practices
- `regulatory_compliance` - IACUC and regulatory requirements
- `biosafety` - Laboratory safety protocols
- `ethics_review` - Research ethics evaluation

### 6. Technical/Scientific Writer

**Expertise Areas**:

- `manuscript_preparation` - Scientific writing and publication
- `grant_writing` - Funding proposal development
- `documentation` - Technical documentation standards
- `communication` - Science communication strategies

## Usage Examples

### Basic Consultation

```python
from src.mcp.client import MCPClient

# Initialize MCP client
mcp_client = MCPClient(host="127.0.0.1", port=9000)
await mcp_client.connect()

# Request consultation
response = await mcp_client.request_persona_consultation(
    expertise_area="cell_culture",
    query="How do I optimize culture conditions for long-term hippocampal neuron viability?",
    context={
        "culture_duration": "21+ days",
        "experiment_type": "LTP",
        "medium": "Neurobasal"
    }
)

print(f"Expert advice: {response['expert_response']}")
print(f"Confidence: {response['confidence']}%")
```

### Capability Discovery

```python
# Get available personas and their capabilities
capabilities = await mcp_client.get_persona_capabilities()

for persona_name, info in capabilities['available_personas'].items():
    print(f"{persona_name}: {info['capabilities']}")
```

### Consultation History

```python
# Review recent consultations
history = await mcp_client.get_persona_history(limit=10)

for consultation in history['consultations']:
    print(f"Request: {consultation['query'][:50]}...")
    print(f"Persona: {consultation['persona_type']}")
    print(f"Status: {consultation['status']}")
    print("---")
```

## Configuration

### Environment Variables

```bash
# Enable persona system
EUNICE_ENABLE_PERSONAS=true

# Persona logging level
EUNICE_PERSONA_LOG_LEVEL=INFO

# AI API configuration for personas
OPENAI_API_KEY=your_openai_key
XAI_API_KEY=your_xai_key
```

### MCP Server Configuration

```python
# config/default_config.json
{
    "mcp_server": {
        "host": "127.0.0.1",
        "port": 9000,
        "enable_personas": true,
        "persona_timeout": 60
    },
    "personas": {
        "default_model": "gpt-4",
        "max_context_tokens": 4000,
        "confidence_threshold": 0.7
    }
}
```

## Testing

### Manual Testing

Use the test client to verify persona system functionality:

```bash
python tests/test_mcp_persona_client.py
```

### Automated Testing

Run persona system tests:

```bash
pytest tests/test_personas/ -v
```

### Test Scenarios

1. **Capability Discovery**: Verify all personas are discoverable
2. **Expert Consultation**: Test consultation request/response cycle
3. **Error Handling**: Test unknown expertise areas and invalid requests
4. **History Tracking**: Verify consultation history persistence
5. **Confidence Scoring**: Validate confidence metrics
6. **Multi-Persona Routing**: Test automatic persona selection

## Error Handling

### Common Error Types

1. **Persona Not Available**: Requested persona is not initialized
2. **Unknown Expertise Area**: Expertise area not recognized
3. **Timeout**: Consultation request times out
4. **AI API Error**: Underlying AI service failure
5. **Invalid Request**: Malformed consultation request

### Error Response Format

```python
{
    "request_id": "consultation_abc123",
    "status": "error",
    "error": "Persona system not available",
    "persona_type": "system"
}
```

## Performance Considerations

### Optimization Strategies

1. **Persona Caching**: Keep initialized personas in memory
2. **Request Batching**: Batch similar consultation requests
3. **Response Caching**: Cache common query responses
4. **Load Balancing**: Distribute requests across persona instances

### Monitoring Metrics

- Consultation request rate
- Average response time
- Persona availability
- Confidence score distribution
- Error rate by persona type

## Security Considerations

### Access Control

- MCP server authentication required
- Client identification and authorization
- Rate limiting on consultation requests

### Data Privacy

- Consultation history encryption
- Sensitive context data handling
- Audit trail for all consultations

## Future Enhancements

### Planned Features

1. **Multi-Modal Consultations**: Support for image/file attachments
2. **Collaborative Consultations**: Multiple personas on single request
3. **Learning Integration**: Persona learning from consultation feedback
4. **Custom Personas**: User-defined domain expert personas
5. **Integration APIs**: External system consultation access

### Research Applications

1. **Experimental Design**: AI-assisted experimental planning
2. **Protocol Optimization**: Real-time protocol refinement
3. **Troubleshooting**: Expert diagnosis of experimental issues
4. **Literature Integration**: Citation and reference suggestions
5. **Cross-Domain Insights**: Interdisciplinary perspective integration

## Troubleshooting

### Common Issues

1. **Persona Not Responding**

   - Check MCP server logs
   - Verify persona initialization
   - Test AI API connectivity

2. **Low Confidence Scores**

   - Review query specificity
   - Provide more context
   - Try different expertise area

3. **Connection Timeouts**
   - Check network connectivity
   - Verify MCP server status
   - Review timeout configurations

### Debug Commands

```bash
# Check MCP server status
curl -X GET http://localhost:9000/health

# View persona logs
tail -f logs/mcp_server.log | grep persona

# Test persona connectivity
python -c "from src.personas.mcp_integration import PersonaMCPIntegration; print('OK')"
```

## Contributing

### Adding New Personas

1. Create persona agent class in `src/personas/`
2. Register persona in `PersonaRegistry`
3. Add expertise area mappings
4. Create documentation and tests
5. Update configuration examples

### Extending Capabilities

1. Define new expertise areas
2. Implement consultation logic
3. Add validation and error handling
4. Update protocol documentation
5. Add comprehensive tests

For detailed development guidelines, see the main [Contributing Guide](../README.md#contributing).
