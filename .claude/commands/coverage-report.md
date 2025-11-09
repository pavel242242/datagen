---
description: Generate and display test coverage report
---

Run tests with coverage tracking and show detailed coverage report.

**Your task:**
1. Run `coverage run -m pytest tests/` to execute tests with coverage
2. Run `coverage report` to show summary
3. Identify modules with low coverage (<75%)
4. Highlight critical gaps:
   - Validation module (target: 80%+)
   - Modifiers (target: 80%+)
   - CLI commands (target: 70%+)
5. Show path to 75% overall coverage goal

**Output format should include:**
- Overall coverage percentage
- Coverage by module/file
- Lines missing coverage
- Priority areas to test

**Example output:**
```
📊 Test Coverage Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall Coverage: 43% (Target: 75%, Gap: -32 points)

High Priority Gaps:
❌ validation/structural.py   0% (549 lines)
❌ cli/commands.py            0% (232 lines)
⚠️  modifiers.py              35% (308 uncovered)

Well Tested:
✅ generators/primitives.py   94%
✅ seed.py                    89%
✅ dag.py                     87%

To reach 75% target:
1. Add validation module tests (+20 points)
2. Add CLI integration tests (+8 points)
3. Complete modifier tests (+4 points)
```

If the user wants to see a specific file's coverage in detail, you can also run:
`coverage report -m <filename>` to show missing lines.
