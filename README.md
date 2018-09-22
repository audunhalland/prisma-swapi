### Setup

```
docker-compose up -d
python3 init_db.py
npm install -g prisma
prisma introspect -i
```

Put generated .prisma file under `datamodel` inside `prisma.yml`