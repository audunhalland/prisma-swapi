### Setup

```
docker-compose up -d
./init_db.py
npm install -g prisma
prisma deploy
```

Graphql api now live on `localhost:4466`

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