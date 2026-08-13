export const meta = {
  name: 'human-docs-file-audit',
  description: 'Convergence verification: confirm 17 applied doc fixes are clean + deep-scan not-yet-covered docs + adversarial cross-review',
  phases: [
    { title: 'Converge', detail: 'verify applied fixes are clean + deep code-truth on `docs/` 문서,09,16,19,21 (not covered before)' },
    { title: 'CrossReview', detail: 'adversarial reviewer: declare convergence (0 new) or list remaining confirmed bugs' },
  ],
}

const FIXED = `
ALREADY FIXED & COMMITTED (verify they are clean now; do NOT re-report unless a fix is wrong/incomplete):
- redfish-gather/library/README.md: line count now "약 4,500 줄 (2026-06 기준)" (no exact number — file is actively changing); dead test_runner + _detect_from_product refs removed; function-index line numbers removed.
- schema/baseline_v1/README.md + `docs/contract/03-fields.md`: dead *_baseline_annotated.jsonc scheme repointed to real schema/output_examples/*.jsonc.
- `docs/contract/04-failure-and-diagnosis.md` + `docs/reference/decision-log.md`: tests/baseline_v1 → schema/baseline_v1. `docs/contract/04-failure-and-diagnosis.md` §4 example: power section added (10 sections).
- `docs/develop/03-adapter-system.md` + `docs/develop/04-add-vendor.md`: vault profile redfish_dell → dell (vault/<loc>/redfish/dell.yml), fallback []. `docs/develop/03-adapter-system.md` priority matrix: hpe_superdome_flex 101, supermicro_x12 in 100 row, hpe_ilo5 alone in 90. `docs/reference/compatibility-matrix.md`: priority=101.
- `docs/contract/04-failure-and-diagnosis.md` + `docs/contract/04-failure-and-diagnosis.md`: diagnosis examples now use nested "details" (channel/adapter_candidate/checked_ports/selected_port/redfish_version/product/systems_uri), no top-level probe_facts.
- `docs/operate/08-ansible-config.md`: forks=200; field_mapper → jedec_mapper. `docs/operate/04-pipeline-runtime.md`: Stage 3 = FAIL gate. `docs/develop/06-debugging.md`: field_dictionary 83; §9 six keys are diagnosis top-level (siblings of details); priority quick-ref vendor 기본=10 (was 50). `docs/contract/01-input.md`: vault/<loc>/redfish/<vendor>.yml. common/README: normalize = 10 files.
- ROUND C fixes: `docs/contract/04-failure-and-diagnosis.md` failure example + FAQ — removed non-existent probe_facts key (merged INTO details by diagnosis_mapper.py). REQUIREMENTS.md §3-1: DL380 Gen11/iLO6 → redfish_hpe_ilo6 (P100); false "no dedicated iLO6 adapter" claim removed. `docs/develop/04-add-vendor.md` priority flowchart: lab 부재 보호 = 101.
- ROUND D fixes: README envelope example matches real shape (diagnosis={reachable,...,details:dict} no precheck; meta no loc; correlation={serial_number,host_ip,bmc_ip,...} no request_id). `docs/reference/compatibility-matrix.md` cell distribution OK=36/OK★=157/GAP=8. `docs/operate/05-vault.md` §2 header restored. `docs/develop/06-debugging.md` generic example score=-20 (−40 penalty).
- ROUND E fixes: failure_stage 4-value set {reachable, port, protocol, auth} now consistent across `docs/contract/04-failure-and-diagnosis.md` (port-closed example uses "port"), `docs/contract/04-failure-and-diagnosis.md` (added port row), `docs/contract/03-fields.md` (added reachable row) — matches precheck_bundle.py (reachable=no response, port=host up+port closed). `docs/contract/03-fields.md` cisco_baseline drift note corrected to hostname==ip (10.100.15.2), not null.
- ROUND G/G2 fix: cross-channel regression counts. `docs/develop/06-debugging.md` bullet command now points to tests/regression/test_cross_channel_consistency.py = 120 (9 baseline × 13 + 3 coverage); the DIRECTORY command pytest tests/regression/ = 158 (120 + HBA/IB 27 + vendor-display 7 + csus-mock 4) — labeled correctly in `docs/develop/06-debugging.md` line 271 and `docs/develop/04-add-vendor.md` line 324. VERIFIED by running pytest --collect-only on both scopes. Do NOT re-flag these counts.
- ROUND I fix: `docs/contract/02-output-envelope.md`:552 FAQ — diagnosis 공통 고정 필드 5→6 (added failure_reason; diagnosis_mapper.py returns reachable/port_open/protocol_supported/auth_success/failure_stage/failure_reason + details). Do NOT re-flag.
- ROUND H fix (owner-approved): Cisco verification status. `docs/develop/03-adapter-system.md` 검증상태 table + REQUIREMENTS §3-1 now say "M4 partial lab 검증 (UCS C220 M4 / CIMC 4.1(2g))" — consistent with `docs/reference/live-validation.md`:484 "partial (M4 lab tested)", `docs/reference/compatibility-matrix.md` M4=OK, and the real evidence file (tests/evidence/2026-04-29-cisco-redfish-critical-review.md). The previous "실장비 미검증" was the imprecise outlier. Do NOT re-flag Cisco lab status. CLAUDE.md "3대 Dell/HPE/Lenovo" is the FULL-Round set (Cisco M4 is partial) — not a contradiction, and CLAUDE.md is harness anyway.
- KNOWN-HISTORICAL / OUT-OF-SCOPE (do NOT report — already ruled out): `docs/reference/live-validation.md` §11/§12 "(14개 YAML)" frozen 2026-03-18 snapshot; `docs/reference/decision-log.md` "107" dated ticket counts; CLAUDE.md "약 3,867줄" harness; tests/regression/conftest.py docstring "8 baseline JSONs" is a CODE comment handled by a separate comment-audit; `docs/develop/06-debugging.md` -vvv "28 candidates" synthetic example.
`

const KNOWN_NONBUGS = `
KNOWN-INTENTIONAL non-bugs (do NOT report): adapters/esxi/esxi_9x.yml + adapters/os/linux_rocky.yml ("(예:)" hypotheticals), vault/<loc>/redfish/hpe.yml (deferred), tests/evidence/vault-rotation-log.md + tests/fixtures/redfish/hpe_ilo7/ (prospective files), `docs/reference/decision-log.md` refs to docs/ai/tickets/**/fixes/*.md (archived harness tickets), `docs/reference/live-validation.md` line ~391 "field_dictionary 65" (dated historical cycle-log record — leave). Multiple-H1 lint + docs/superpowers archive = deferred owner decisions, NOT bugs.
NOTE: a concurrent process is editing Python COMMENTS, so .py line counts drift — do NOT report exact Python line-count mismatches.
`

const RULES = `
HARD CONSTRAINTS: Analysis only, do NOT edit. Never propose deleting code/contract files. docs/ai/**, .claude/**, CLAUDE.md, docs/superpowers/** = harness (out of scope). Canonical human docs: flag only FACTUAL problems (wrong counts/paths/commands, broken links, contradictions), never style. Every finding MUST cite evidence you actually Read/ran; confidence 'confirmed' only if you verified BOTH doc claim and code reality.
`

const FINDINGS = {
  type: 'object', additionalProperties: false,
  properties: {
    summary: { type: 'string' },
    fixes_verified_clean: { type: 'boolean', description: 'true if all 17 applied fixes are now correct in the docs' },
    findings: { type: 'array', items: {
      type: 'object', additionalProperties: false,
      properties: {
        category: { type: 'string', enum: ['doc_code_mismatch','broken_link','contradiction','stale_content','navigation_gap','fix_incomplete','other'] },
        severity: { type: 'string', enum: ['HIGH','MED','LOW'] },
        file: { type: 'string' }, location: { type: 'string' },
        problem: { type: 'string' }, evidence: { type: 'string' },
        proposed_action: { type: 'string' }, confidence: { type: 'string', enum: ['confirmed','likely','uncertain'] },
      }, required: ['category','severity','file','problem','evidence','proposed_action','confidence'],
    } },
  }, required: ['summary','fixes_verified_clean','findings'],
}

phase('Converge')
const codeTruth = await agent(`You are the convergence verifier for the server-exporter human-docs audit (cwd C:\\github\\server-exporter).
${RULES}
${FIXED}
${KNOWN_NONBUGS}
TWO TASKS:
1) VERIFY each "ALREADY FIXED" item above is now correct in the actual doc (open the file, confirm the corrected value matches the code/reality). Set fixes_verified_clean accordingly; emit a 'fix_incomplete' finding for any fix that is wrong or partial.
2) FINAL CONVERGENCE SWEEP across ALL human docs (README.md, REQUIREMENTS.md, `docs/operate/01-jenkins-master.md`..23, code-dir READMEs). This is round 10 — nine prior rounds fixed 32 bugs (trend 4→13→4→4→3→1→1→1→1). The corpus is now factually accurate; the last four rounds each found a single isolated LOW value/count nit. ONLY report a GENUINE reader-misleading factual error with hard code/file evidence you personally verified BOTH sides of. An EMPTY findings list is the correct and expected result — do NOT manufacture nitpicks (wording, whitespace, historical snapshots, intentional examples, code comments, or restating already-fixed items). ONLY report a GENUINE reader-misleading factual error a developer would actually trip on, with code evidence. If the docs are now factually accurate, set fixes_verified_clean=true and state 'CONVERGED — no new factual bugs' in summary. Do NOT manufacture nitpicks (whitespace, wording, dated historical snapshots, intentional examples, code comments) to appear thorough — an empty findings list is the correct and expected result if the docs are clean. Cross-check FALSIFIABLE claims (paths, commands, counts, vault filenames, section/field names, envelope/diagnosis shape, adapter priorities, vendor lists, Jenkins stages) against the actual repo. Pay special attention to cross-doc CONSISTENCY (the same fact stated in 2+ docs must agree) and to the docs least-scanned so far (06, 07, 09, 16, 19, 21). Report ONLY confirmed NEW factual bugs not already in the FIXED/known-nonbug lists. If you find nothing new, state 'CONVERGED — no new factual bugs' explicitly in summary. Do NOT manufacture LOW-value nitpicks to appear thorough; only real reader-misleading factual errors.`, { label: 'converge-verify-final', phase: 'Converge', schema: FINDINGS })

phase('CrossReview')
const CROSS = {
  type: 'object', additionalProperties: false,
  properties: {
    converged: { type: 'boolean', description: 'true if NO new confirmed bugs remain (audit may terminate)' },
    verdict_summary: { type: 'string' },
    remaining_confirmed_bugs: { type: 'array', items: {
      type: 'object', additionalProperties: false,
      properties: { file: { type: 'string' }, action: { type: 'string' }, severity: { type: 'string' }, why_real: { type: 'string' } },
      required: ['file','action','severity','why_real'],
    } },
    rejected: { type: 'array', items: { type: 'string' } },
  }, required: ['converged','verdict_summary','remaining_confirmed_bugs','rejected'],
}
const cross = await agent(`You are the Final Cross Reviewer for the server-exporter docs audit (cwd C:\\github\\server-exporter).
${RULES}
The orchestrator has applied 17 factual doc fixes across two commits. Below is the convergence verifier's report. ADVERSARIALLY review: spot-check its top claims yourself by reading the actual file/code (rule 25 R7). Reject anything cosmetic/unverifiable/already-known. Decide 'converged' = true only if there are NO new confirmed factual bugs left to fix. List any genuinely remaining confirmed bugs with why_real.

VERIFIER REPORT:
${JSON.stringify(codeTruth)}
`, { label: 'cross-reviewer', phase: 'CrossReview', schema: CROSS })

return { codeTruth, cross }
