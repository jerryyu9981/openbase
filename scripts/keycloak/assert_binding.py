"""真实 Keycloak realm 落库断言（OB-AUTH-OIDC v1.5.0）.

检查共享 PG：oidc_identity(issuer=http://127.0.0.1:8080/realms/openbase) 映射、
绑定用户与 user_role（org_admin/user）是否随真实 Keycloak 登录持久化。
用法: python scripts/keycloak/assert_binding.py
"""
import psycopg2

ISSUER = "http://127.0.0.1:8080/realms/openbase"
PG_DSN = "postgresql://nuct:nuct123456@192.168.0.151:5432/nuct"
results = []


def check(name: str, cond: bool, detail: str = "") -> None:
    results.append((name, bool(cond), detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {detail}")


conn = psycopg2.connect(PG_DSN)
cur = conn.cursor()
cur.execute("SET search_path TO openbase")

print("=== 真实 Keycloak（8080/realms/openbase）绑定落库 ===")
cur.execute(
    "SELECT user_id, sub, issuer FROM oidc_identity WHERE issuer=%s ORDER BY user_id",
    (ISSUER,),
)
rows = cur.fetchall()
check(f"oidc_identity 存在 issuer={ISSUER} 映射", len(rows) >= 1, str(rows))

for user_id, sub, _iss in rows:
    cur.execute("SELECT username, email FROM users WHERE id=%s", (user_id,))
    u = cur.fetchone()
    cur.execute(
        "SELECT r.code FROM roles r JOIN user_role ur ON ur.role_id=r.id WHERE ur.user_id=%s",
        (user_id,),
    )
    codes = [r[0] for r in cur.fetchall()]
    print(f"  user_id={user_id} username={u and u[0]} sub={sub[:24]}... roles={codes}")
    if u and u[0].startswith("oidc-admin"):
        check("oidc-admin 绑定 org_admin", "org_admin" in codes, str(codes))
    if u and u[0].startswith("oidc-user"):
        check("oidc-user 绑定 user", "user" in codes, str(codes))

conn.close()
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
print(f"\nPASS {passed} / FAIL {failed} / 总数 {len(results)}")
raise SystemExit(1 if failed else 0)
