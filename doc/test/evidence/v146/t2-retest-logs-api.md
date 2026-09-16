===== T2 API RETEST (Step 4 re-entry) - corrected expectations =====

---- 4 sources: search / facets ----
[PASS] l1_file search                       -> 200
[PASS] l1_file facets                       -> 200
[PASS] audit_db search                      -> 200
[PASS] audit_db facets                      -> 200
[PASS] test_record search                   -> 200
[PASS] test_record facets                   -> 200
[PASS] repo_log search                      -> 200
[PASS] repo_log facets                      -> 200

---- export (l1_file over limit = 400 by design) ----
[PASS] audit_db export csv                  -> 200
[PASS] test_record export csv               -> 200
[PASS] repo_log export csv                  -> 200
[PASS] repo_log export json                 -> 200
[PASS] l1_file export csv (over limit)      -> 400

---- validation branches (unified envelope PARAM_422) ----
[PASS] invalid source                       -> 422
[PASS] page=0                               -> 422
[PASS] page_size=1000                       -> 422
[PASS] export format=xml                    -> 422
[PASS] no token (401 gate)                  -> 401

===== SUMMARY: PASS 18 | FAIL 0 =====
