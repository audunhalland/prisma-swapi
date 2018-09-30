### Setup

```
docker-compose up -d
./init_db.py
npm install -g prisma
prisma deploy
```

Put generated .prisma file under `datamodel` inside `prisma.yml`

### Example mutation
```
mutation {
  createFilm(data: {
    title: "Star Wars"
  }) {
    id
  }
}
```