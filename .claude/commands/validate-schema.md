---
description: Generate data from a schema and validate output in one command
---

Generate synthetic data from a schema file and immediately validate the output.

**Usage Examples:**
- `/validate-schema examples/simple_users_events.json` - Generate and validate simple schema
- `/validate-schema examples/ecomm.json` - Generate and validate e-commerce schema
- `/validate-schema examples/bank.json --seed 42` - Use specific seed

**Your task:**
1. Parse the schema path from the user's request
2. Run `datagen generate <schema> --seed <seed> -o ./output_temp`
3. Run `datagen validate <schema> --data ./output_temp`
4. Report the validation results, including:
   - Quality score
   - Number of validations passed/failed
   - Key issues if any
5. Clean up temp output if desired

**Default seed:** 42 (unless user specifies different)

**Output directory:** Use `./output_temp` to avoid overwriting existing output

If validation fails, explain:
- What constraints were violated
- Which tables/columns have issues
- Recommendations for fixing the schema

Always provide a summary like:
```
✅ Generated 3 tables (15,234 rows total)
✅ Quality Score: 95.4/100
✅ All primary keys unique
✅ All foreign keys valid
⚠️  2 behavioral targets not met
```
