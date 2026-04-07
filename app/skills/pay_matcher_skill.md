# GRIFFIN Pay Matcher Skill

**Description**: Takes a classified DHRM career group and role, identifies the corresponding pay band, crosswalks it to the William & Mary pay grade, retrieves Virginia salary data, and produces a compensation recommendation.

---

## Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `career_group` | string | Yes | DHRM career group name or code (e.g., "Information Technology" or "IT"). Must match an entry in the career groups reference data. |
| `role_code` | string | Yes | DHRM role code (e.g., "IT Specialist III"). Must match an entry in the roles reference data within the specified career group. |
| `location` | string | No | Geographic location for salary data lookup. Default: "Virginia". Used when querying external salary APIs (e.g., CareerOneStop) for market comparison. |

---

## Reference Data

This skill requires access to the GRIFFIN DHRM reference dataset:

- **Roles** (`roles.xlsx`): 294 roles across 56 career groups, organized into bands 1-9. Each role maps to a specific pay band.
- **Crosswalk** (`crosswalk.xlsx`): DHRM pay band to William & Mary pay grade mapping:

  | DHRM Pay Band | DHRM Min | DHRM Max | W&M Pay Grade | W&M Min | W&M Midpoint | W&M Max |
  |:---:|---:|---:|:---:|---:|---:|---:|
  | 1 | $28,360 | $65,631 | S01 | $32,240 | $36,989 | $41,738 |
  | 2 | $30,511 | $80,875 | S01 | $32,240 | $36,989 | $41,738 |
  | 3 | $33,828 | $93,557 | S07 | $32,240 | $53,091 | $73,942 |
  | 4 | $44,192 | $117,360 | S10 | $42,514 | $70,465 | $98,417 |
  | 5 | $57,733 | $148,455 | S13 | $56,587 | $93,789 | $130,991 |
  | 6 | $75,423 | $189,075 | S16 | $75,317 | $124,833 | $174,349 |
  | 7 | $98,535 | $242,152 | S18 | $91,133 | $151,048 | $210,964 |
  | 8 | $128,721 | $311,485 | S21 | $121,299 | $201,046 | $280,793 |
  | 9 | $168,166 | -- | S23 | $146,771 | $238,318 | $339,760 |

- **SOC Codes** (`soc_codes.xlsx`): Standard Occupational Classification codes for each role, used to query external salary APIs.

---

## Instructions

You are an expert Virginia DHRM compensation analyst. Follow these steps in order, showing your work at each step.

### Step 1: DHRM Pay Band Identification

1. Look up the `role_code` within the `career_group` in the roles reference data.
2. Identify the pay band (1-9) assigned to that role.
3. Report the DHRM pay band range (minimum and maximum salary for that band).

If the `role_code` is not found within the specified `career_group`, report an error and list the valid roles for that career group.

### Step 2: W&M Crosswalk Lookup

1. Using the pay band identified in Step 1, look up the corresponding William & Mary pay grade in the crosswalk table.
2. Report the W&M pay grade (S01-S23) and its full salary range:
   - Minimum
   - Midpoint
   - Maximum

Note: DHRM bands 1 and 2 both map to W&M grade S01. If the role is in band 2, note that the DHRM range is wider than the W&M grade range, which may affect placement.

### Step 3: Virginia Salary Data Retrieval

1. Identify the SOC code associated with the role (from the SOC codes reference data).
2. Query external salary data for that SOC code in the specified `location` (default: Virginia).
   - Primary source: CareerOneStop API (Virginia-localized salary by SOC code).
   - Fallback: Tavily web search for "[SOC code] salary Virginia" if the API is unavailable.
3. Report the external market data:
   - Median salary
   - 25th percentile
   - 75th percentile
   - Source and date of the data

If no external data is available, note this and proceed with internal data only.

### Step 4: Compensation Recommendation

Synthesize the internal and external data into a recommendation:

1. **Internal Range**: Report the W&M pay grade range from Step 2 as the institutional salary band.
2. **Market Comparison**: Compare the W&M range against the external Virginia salary data from Step 3.
   - If the W&M midpoint is within 10% of the market median, the grade is market-aligned.
   - If the W&M midpoint is more than 10% below the market median, flag a potential below-market concern.
   - If the W&M midpoint is more than 10% above the market median, note the premium positioning.
3. **Placement Guidance**: Suggest where within the W&M range a new hire or reclassified employee might be placed:
   - **Minimum to midpoint**: Entry-level qualifications, limited experience in the specific role.
   - **Midpoint**: Fully qualified, meeting all position requirements with solid experience.
   - **Midpoint to maximum**: Exceptional qualifications, extensive experience, or critical retention scenario.

### Step 5: Produce Compensation Output

Present the results in this format:

```
COMPENSATION SUMMARY
  Role: [role_code] in [career_group]
  DHRM Pay Band: [band number]
  W&M Pay Grade: [grade]

INTERNAL SALARY RANGE (W&M)
  Minimum:  $[amount]
  Midpoint: $[amount]
  Maximum:  $[amount]

DHRM SALARY RANGE
  Minimum:  $[amount]
  Maximum:  $[amount]

MARKET DATA ([location])
  SOC Code: [code]
  25th Percentile: $[amount]
  Median:          $[amount]
  75th Percentile: $[amount]
  Source: [source name], [date]

MARKET ALIGNMENT
  W&M Midpoint vs. Market Median: [+/-]X%
  Assessment: [Market-aligned | Below market | Above market]

PLACEMENT GUIDANCE
  [Narrative recommendation based on Step 4 logic]
```

### Handling Blended Classifications

If the Classifier Skill produced a blended classification with two roles, run the pay matching process for **both** the primary and secondary roles, then calculate the weighted compensation:

1. Look up pay band and W&M grade for both roles.
2. Calculate weighted salary ranges using the duty percentages from the classification:
   - Weighted Min = (Primary Min x Primary%) + (Secondary Min x Secondary%)
   - Weighted Midpoint = (Primary Midpoint x Primary%) + (Secondary Midpoint x Secondary%)
   - Weighted Max = (Primary Max x Primary%) + (Secondary Max x Secondary%)
   - Where Primary% and Secondary% are normalized to sum to 100%.
3. Show the math and present both the individual and weighted ranges.
