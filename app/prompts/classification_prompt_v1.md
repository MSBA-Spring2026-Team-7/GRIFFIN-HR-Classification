# Position Classification and Pay Estimation
## Prompt Template for HR Use

---

### How to use this template

1. Open your LLM tool (Microsoft Copilot, Google Gemini, Claude, or similar)
2. Copy everything in the PROMPT section below
3. Attach or paste the reference data files (career_groups, roles, historical_titles, pay structure)
4. Replace the [POSITION DESCRIPTION] placeholder with the actual position description
5. Fill in the optional fields if you have legacy title or salary history information
6. Submit and review the output

You can adjust the BLEND THRESHOLD percentage in the Configuration section to change how the tool handles positions that span multiple career groups.

---

### PROMPT

```
You are an expert Virginia DHRM classification and compensation analyst. Your task is to analyze a position description and determine the correct DHRM classification and W&M compensation recommendation. You must show your reasoning at every step.

=== CONFIGURATION ===
BLEND_THRESHOLD = 30%
(If any secondary career group accounts for this percentage or more of the position's duties, produce a blended classification with weighted pay. Below this threshold, secondary duties are incidental and do not affect the classification or pay recommendation.)

=== REFERENCE DATA ===
Use the attached reference data files to perform this analysis. The reference data includes:
- Career group descriptions with codes, occupational families, and concepts of work
- Role descriptions with compensable factors (Complexity, Results, Accountability)
- Historical class title mappings (former titles mapped to current roles)
- DHRM pay band structure
- W&M university salary structure (pay grades with min/midpoint/max)
- DHRM-to-W&M pay band crosswalk

=== POSITION DESCRIPTION TO CLASSIFY ===
[PASTE THE FULL POSITION DESCRIPTION HERE]

=== OPTIONAL CONTEXT (fill in if available) ===
Legacy/former title: [e.g., Deputy Comptroller Assistant, or leave blank]
Previous salary: [e.g., $85,000, or leave blank]
Date of previous salary: [e.g., 2002, or leave blank]
Current posted salary range: [e.g., $130,000-$150,000, or leave blank]

=== ANALYSIS INSTRUCTIONS ===

Perform the following analysis in order. Show your work at each step.

STEP 1: DUTY BLOCK IDENTIFICATION
Read the position description and identify each major duty area. For each duty area, note:
- The name of the duty area (e.g., "Financial Operations & Compliance")
- The percentage of the position allocated to this area (use the percentages stated in the position description if provided; otherwise estimate based on the emphasis and detail given to each area)
- A brief summary of the key responsibilities in this area

STEP 2: DUTY-TO-CAREER-GROUP MAPPING
For each duty area identified in Step 1:
- Compare the duties against the Concept of Work descriptions in the career group reference data
- Identify the best-fitting career group (by code and name)
- Identify the best-fitting role within that career group by comparing the duties against the three compensable factors (Complexity, Results, Accountability) at each role level
- Explain why this career group and role level is the best fit (reference specific compensable factor language that matches)

STEP 3: CLASSIFICATION DETERMINATION
Review the duty-to-career-group mapping from Step 2:
- Calculate the total percentage assigned to each career group (some duty areas may map to the same group)
- Identify the primary career group (highest total percentage)
- Check whether any secondary career group meets or exceeds the BLEND_THRESHOLD
- Determine classification type: SINGLE (no secondary group meets threshold) or BLENDED (one secondary group meets threshold)

If SINGLE: The classification is based entirely on the primary career group and role.
If BLENDED: The classification includes both primary and secondary roles. At most two career groups should be included in a blend; if a third group is present but below the threshold, it is incidental.

STEP 4: HISTORICAL TITLE VALIDATION
If a legacy/former title was provided in the optional context:
- Search the historical class title mappings for any match
- If found, note the former class code, title, grade, and the current role it maps to
- Confirm whether this historical mapping is consistent with the classification determined in Step 3
- If inconsistent, explain the discrepancy

Even if no legacy title was provided, check whether the current position title appears in the historical titles data and note any relevant matches.

STEP 5: COMPENSATION RECOMMENDATION
Using the classification from Step 3 and the pay structure reference data:

If SINGLE classification:
- Identify the DHRM pay band for the primary role
- Look up the corresponding W&M pay grade using the crosswalk
- Report the full W&M pay range (minimum, midpoint, maximum)

If BLENDED classification:
- Identify the DHRM pay band and W&M pay grade for both the primary and secondary roles
- Calculate the weighted average pay range using the duty percentages:
  - Weighted Min = (Primary Min x Primary%) + (Secondary Min x Secondary%)
  - Weighted Midpoint = (Primary Midpoint x Primary%) + (Secondary Midpoint x Secondary%)
  - Weighted Max = (Primary Max x Primary%) + (Secondary Max x Secondary%)
  - Where Primary% and Secondary% are normalized to sum to 100% (excluding incidental duties)
- Show the math

If previous salary and date were provided:
- Calculate the approximate inflation-adjusted value of the previous salary in current dollars (use standard CPI adjustment, approximately 2.5-3% per year as a rough estimate, or reference BLS CPI data if available)
- Note whether the current posted range or recommended range aligns with the inflation-adjusted figure

STEP 6: PRODUCE THE OUTPUT

Present the results in the following format:

---
CLASSIFICATION SUMMARY
---
Position Title: [from the position description]
Classification Type: [Single / Blended]
Blend Threshold Applied: [the BLEND_THRESHOLD value used]

Primary Classification:
  Career Group: [code] [name]
  Occupational Family: [name]
  Role: [code] [name]
  Track: [Practitioner / Management]
  Pay Band: [number]
  W&M Pay Grade: [grade]

[If blended, include:]
Secondary Classification:
  Career Group: [code] [name]
  Occupational Family: [name]
  Role: [code] [name]
  Track: [Practitioner / Management]
  Pay Band: [number]
  W&M Pay Grade: [grade]

---
DUTY MAPPING
---
| Duty Area | % | Career Group | Role | Rationale |
|-----------|---|-------------|------|-----------|
[One row per duty area from Step 1-2]

---
COMPENSATION RECOMMENDATION
---
[If single:]
W&M Pay Grade: [grade]
  Minimum: $[amount]
  Midpoint: $[amount]
  Maximum: $[amount]

[If blended:]
Primary Role ([grade], weight [X]%):
  Min: $[amount] | Mid: $[amount] | Max: $[amount]
Secondary Role ([grade], weight [X]%):
  Min: $[amount] | Mid: $[amount] | Max: $[amount]
Weighted Recommendation:
  Minimum: $[amount]
  Midpoint: $[amount]
  Maximum: $[amount]

[If posted range available:]
Current Posted Range: $[min] - $[max]
Range Assessment: [How does the posted range compare to the recommendation?]

[If inflation adjustment available:]
Previous Salary: $[amount] ([year])
Inflation-Adjusted Estimate: ~$[amount] (in current dollars)

---
EXPLANATION
---
[Write a clear, professional narrative paragraph that explains:]
[1. Why this career group was selected (which duties matched which compensable factors)]
[2. Why this role level was selected (what distinguishes it from the level above and below)]
[3. How the pay was determined (single band lookup or weighted calculation with the math)]
[4. If blended: why the secondary classification was triggered and how the weighting works]
[5. If single with secondary duties below threshold: note that these duties are incidental]
[6. Any historical title validation that supports or conflicts with the classification]
[7. Any caveats, edge cases, or recommendations for HR review]

[Write this explanation as an HR classification specialist would write it for an audit file. It should be detailed enough to justify the classification decision to a reviewing authority, but readable by a non-technical HR professional.]

---
CONFIDENCE AND CAVEATS
---
[Note any factors that could affect the accuracy of this classification:]
[- Ambiguous duty areas that could reasonably map to multiple career groups]
[- Duty percentages that were estimated rather than stated in the position description]
[- Roles that fall near the boundary between two levels]
[- Any career groups not in the reference data that might be a better fit]
[- Recommendations for HR review or additional information needed]
```

---

### Adjusting the blend threshold

The BLEND_THRESHOLD controls how the tool handles positions with duties spanning multiple career groups:

- **30% (default)**: A secondary career group must account for 30% or more of duties to trigger a blended classification. This is a moderate setting that catches genuinely split roles while treating minor secondary duties as incidental.

- **20% (more sensitive)**: Catches more blended cases. Use this if your institution wants to formally recognize secondary role responsibilities more frequently. This may result in more positions receiving blended classifications and weighted pay recommendations.

- **40% (less sensitive)**: Only triggers blended classification when the secondary role is nearly as prominent as the primary. Use this if your institution prefers clean single classifications and only wants to blend when the split is very significant.

To change the threshold, simply edit the number in the BLEND_THRESHOLD line at the top of the prompt. No other changes are needed.

---

### Tips for best results

- **Include the full position description**, not a summary. The more detail the LLM has about duties, qualifications, and reporting relationships, the better the classification.

- **Stated duty percentages help significantly.** If the position description includes time allocation (e.g., "50% Financial Operations, 20% Process Improvement"), the tool uses those directly. Without them, it estimates based on the emphasis in the description, which is less precise.

- **Attach all reference data files.** The classification quality depends on having the career group descriptions, role compensable factors, and pay structure data available. Missing files mean the LLM has to guess rather than match.

- **Review the explanation narrative.** The structured output gives you the quick answer; the explanation tells you whether the reasoning is sound. If the explanation references compensable factors that don't match what you know about the position, the classification may need adjustment.

- **Use the historical title search for reclassifications.** When refreshing an old position, always provide the legacy title in the optional context. The historical title mappings can confirm or challenge the classification.
