# onshape-AI
 
 flask run in termina    (you may need to export it first. copy error message into cursor if needed)

Example request curl -X POST http://localhost:5000/v1/chat/ \
     -H "Content-Type: application/json" \
     -d '{
       "message": "tell me about the document here  https://cad.onshape.com/documents/34194a7792ea9db6d10188d3/w/2603dadfb9d5ccf8117390d0/e/ff8bd4f1cd0882be07172a4d"
     }'