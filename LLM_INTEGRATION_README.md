# LLM Integration - Phase 5

**Status**: ✅ Implemented and Tested

## Overview

LLM integration enables natural language schema generation in **two ways**:

### 🌟 Primary: Conversational Template (Recommended)
Copy/paste a prompt into ChatGPT/Claude/GPT-5 and have a **natural conversation** about your dataset. The LLM asks clarifying questions and outputs valid JSON. **No API keys needed!**

### ⚙️ Optional: Programmatic API
For automation workflows, use the CLI/Python API with Anthropic API key for headless schema generation.

---

## Conversational Template (Primary Method)

### How It Works

1. **Copy the prompt** from [`SCHEMA_GENERATION_PROMPT.md`](SCHEMA_GENERATION_PROMPT.md)
2. **Open ChatGPT, Claude, or GPT-5** (web interface - no API key!)
3. **Paste the entire prompt** to start a new conversation
4. **Describe your dataset** naturally: "I need e-commerce tracking"
5. **LLM asks clarifying questions**: "How many users? Time period?"
6. **Answer naturally**: "500 users, Jan-Dec 2024"
7. **Get valid JSON** ready to save and use
8. **Run**: `datagen generate schema.json --seed 42`

### Why This Approach?

✅ **No API keys needed** - Use free ChatGPT/Claude web interface
✅ **Human-in-the-loop** - Clarify ambiguities through conversation
✅ **Natural language** - No need to learn DSL syntax
✅ **Iterative refinement** - Ask for changes: "Add a status field"
✅ **Educational** - Learn the DSL through examples

### Example Conversation

See [`EXAMPLE_CONVERSATION.md`](EXAMPLE_CONVERSATION.md) for full examples.

**Quick example:**

```
You: I need SaaS subscription tracking

LLM: Great! A few questions:
     1. How many users and subscription plans?
     2. Should there be state transitions?
     3. Time period?

You: 200 users, 3 plans, track state changes, Jan-Dec 2024

LLM: [Outputs complete JSON schema with users, plans, subscriptions, and payments]
```

### The Prompt Template

The prompt in [`SCHEMA_GENERATION_PROMPT.md`](SCHEMA_GENERATION_PROMPT.md) includes:

- **Role definition**: "You are an expert data architect..."
- **Conversation guidelines**: Ask 2-3 questions before generating
- **Complete DSL specification**: All generator types, modifiers, structure rules
- **Examples**: Mini-schema showing best practices
- **Output format**: JSON-only, no markdown
- **Validation reminders**: Foreign keys, UTC format, etc.

---

## Programmatic API (Optional)

For automation, CI/CD, or headless workflows:

## Features

- **Natural Language → JSON Schema**: Convert descriptions like "E-commerce with users, products, and orders" into complete schemas
- **Validation Loop**: Automatic Pydantic validation after generation
- **Auto-Repair**: Up to 3 automatic repair attempts on validation errors
- **Constrained Output**: JSON-only output with strict formatting rules
- **Error Recovery**: Intelligent error messages guide LLM to fix issues

## Architecture

```
User Description
     ↓
System Prompt (Rules + Examples)
     ↓
Claude API (Sonnet 4)
     ↓
JSON Schema Output
     ↓
Pydantic Validation ──→ Valid? ──→ Return
     ↓ (errors)
Auto-Repair Prompt
     ↓
Claude API (Retry)
     ↓
... (max 3 retries)
```

## Usage

### CLI Command

```bash
# Basic usage (output to stdout)
export ANTHROPIC_API_KEY=your-key-here
datagen create -d "E-commerce with users, products, and orders"

# Save to file
datagen create -d "SaaS subscription tracking" -o saas.json

# Use specific model
datagen create -d "Healthcare appointments" --model claude-sonnet-4-20250514

# Customize retry attempts
datagen create -d "IoT sensor data" --max-retries 5
```

### Programmatic Usage

```python
from datagen.llm import generate_schema_from_description

# Generate schema
schema_dict, dataset = generate_schema_from_description(
    description="E-commerce with users, products, and orders",
    model="claude-sonnet-4-20250514",
    max_retries=3,
)

# Access validated schema
print(f"Generated: {dataset.metadata.name}")
print(f"Tables: {len(dataset.nodes)}")

# Use schema for generation
from datagen.core.executor import generate_dataset
generate_dataset(dataset, master_seed=42, output_dir="./output")
```

## File Structure

```
src/datagen/llm/
├── __init__.py              # Package exports
├── prompts.py               # System/user/repair prompts
└── schema_generator.py      # Main generator with validation loop
```

## Prompts

### System Prompt
Defines the role, rules, and examples:
- Schema structure requirements
- Generator types (sequence, choice, faker, etc.)
- Modifier types (jitter, multiply, clamp, etc.)
- Response format (JSON-only, no markdown)
- Mini-example schema

### User Prompt
Customized per request:
- User's natural language description
- Requirements for realistic names, relationships, row counts
- Instructions to use appropriate generators

### Repair Prompt
Used on validation errors:
- Shows invalid schema
- Lists specific validation errors
- Common fixes (missing fields, typos, format issues)

## Example Generated Schema

**Input**: "E-commerce with users, products, and orders"

**Output**: See `examples/llm_generated_ecommerce.json`
- 4 tables: user, product, order, order_item
- Realistic generators (faker, lognormal, poisson)
- Proper relationships (FK lookups)
- Modifiers for realism (jitter)
- Validates and generates successfully

## Validation & Auto-Repair

### Validation Checks
1. **JSON Parse**: Valid JSON structure
2. **Pydantic**: Schema matches Datagen DSL spec
3. **Field Presence**: All required fields present
4. **Generator Types**: Valid generator names
5. **References**: Parent tables exist for FK lookups

### Common Auto-Repairs
- Add missing `constraints` field
- Fix generator type typos (e.g., "choce" → "choice")
- Add missing `from` in lookup generators
- Fix datetime format (add Z suffix)
- Correct field name typos (e.g., "colums" → "columns")

### Retry Strategy
- **Attempt 1**: Initial generation
- **Attempt 2-4**: Auto-repair with error feedback
- **Max Retries**: 3 by default (configurable)
- **Failure**: Raise ValueError with detailed error

## Testing

### Test Generated Schema
```bash
# Generate schema
datagen create -d "Simple users and events" -o test.json

# Validate schema
python -c "from datagen.core.schema import validate_schema; import json; validate_schema(json.load(open('test.json')))"

# Generate data
datagen generate test.json --seed 42 -o output_test

# Verify output
ls output_test/*.parquet
```

### Validated Example
The `examples/llm_generated_ecommerce.json` schema:
- ✅ Validates with Pydantic
- ✅ Generates 6,844 events across 4 tables
- ✅ Proper FK relationships
- ✅ Realistic distributions

## Configuration

### Environment Variables
```bash
# Required
export ANTHROPIC_API_KEY=your-key-here

# Optional (defaults shown)
export DATAGEN_LLM_MODEL=claude-sonnet-4-20250514
export DATAGEN_LLM_MAX_TOKENS=4096
export DATAGEN_LLM_MAX_RETRIES=3
```

### Model Options
- `claude-sonnet-4-20250514` (default) - Balance of speed/quality
- `claude-opus-4-20250514` - Highest quality, slower
- `claude-3-5-sonnet-20241022` - Previous version

## Limitations

1. **API Key Required**: Must have valid Anthropic API key
2. **Cost**: Each generation costs ~$0.01-0.10 depending on complexity
3. **Complex Schemas**: Very large schemas (10+ tables) may require multiple attempts
4. **Domain Knowledge**: Generic schemas work best; domain-specific may need manual refinement
5. **Advanced Features**: Phase 4 features (state machines, attribution, diffusion) not yet prompted

## Future Enhancements (Roadmap)

### v1.1
- [ ] Clarification questions (≤2 yes/no) for ambiguous descriptions
- [ ] Example-based learning (few-shot prompts)
- [ ] Schema refinement mode (iterative improvement)

### v1.2
- [ ] Phase 4 feature prompts (state machines, attribution, etc.)
- [ ] Multi-model support (OpenAI, local models)
- [ ] Cost estimation before generation

### v2.0
- [ ] Interactive schema builder (chat interface)
- [ ] Schema templates library
- [ ] Automatic row count estimation from description

## Contributing

When modifying LLM integration:

1. **Update Prompts**: Edit `prompts.py` for schema structure changes
2. **Test Validation**: Ensure auto-repair works with new error types
3. **Add Examples**: Create example schemas in `examples/llm_generated_*.json`
4. **Document**: Update this README with new capabilities

## Support

**Issues**: Submit to GitHub Issues with:
- Natural language description used
- Generated schema (if any)
- Error messages
- Expected vs actual behavior

**Examples**: See `examples/` directory for validated schemas

**Docs**: See main README.md for Datagen usage

---

**Last Updated**: 2024-11-10
**Version**: 1.0 (Phase 5 Complete)
**Status**: Production-Ready ✅
