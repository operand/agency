To run this demo application:

```sh
OPENAI_API_KEY=_YOUR_API_KEY_HERE_
docker build -t demo .
docker run -it -p 8080:8080 -e OPENAI_API_KEY=$OPENAI_API_KEY --rm demo
```