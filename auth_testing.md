# LUMIÈRE — Auth Testing (Emergent Google Auth)

Auth uses Emergent-managed Google OAuth. No app-managed passwords.

## Collections
- `users`: fields `user_id` (custom UUID like `user_xxxx`), `email`, `name`, `picture`, `created_at`. MongoDB `_id` is internal, always excluded with `{"_id": 0}`.
- `user_sessions`: `user_id`, `session_token`, `expires_at` (7 days), `created_at`.

## Create a test user + session (mongosh)
```
mongosh --eval '
use("test_database");
var userId = "user_" + Date.now();
var token = "test_session_" + Date.now();
db.users.insertOne({user_id:userId, email:"tester_"+Date.now()+"@lumiere.test", name:"Test Creator", picture:"", created_at:new Date().toISOString()});
db.user_sessions.insertOne({user_id:userId, session_token:token, expires_at:new Date(Date.now()+7*24*3600*1000), created_at:new Date()});
print("TOKEN="+token); print("USER="+userId);
'
```

## Backend API test (token via Bearer)
```
API=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d= -f2)
curl -s $API/api/auth/me -H "Authorization: Bearer TOKEN"
curl -s -X POST $API/api/experiences -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" -d '{"title":"Coastal Road Trip","type":"travel"}'
```

## Browser (Playwright) — set cookie AND localStorage token
The frontend reads `session_token` cookie for API auth, and `localStorage.lumiere_token` for media file URLs (`/api/files/{path}?auth=`).
```
await page.context.add_cookies([{ "name":"session_token","value":"TOKEN","domain":"<host>","path":"/","httpOnly":True,"secure":True,"sameSite":"None"}])
await page.add_init_script("localStorage.setItem('lumiere_token','TOKEN')")
await page.goto("<app>/studio")
```

## Success
- `/api/auth/me` returns user (200), dashboard loads at `/studio`, not redirected to `/`.
