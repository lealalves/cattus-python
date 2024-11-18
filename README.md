# Cattus API NodeJs

Repositório da API consumida pelo Mobile [Cattus Mobile]()

## Instalação

    pip install -r requirements.txt

## Rodando a aplicação

    python app.py
    
# Documentação
## ESP32-CAM
  Para utilizar a ESP32-CAM, é necessário estar na mesma rede que ela, para isso, ao ligar ela, após o upload do arquivo .ino do repositório, siga o passo a passo:
  
  - Conecte a rede ``ESP32Cam_AP``.
  - Acesse pelo navegador o IP a rede.
  - Com o painel aberto, conecte a um WiFi.
  - Após conectar a um WiFi, acesse o IP que foi designado a ``ESP32-CAM`` nessa rede.

  Na linha 15 do _app.py_ voce adiciona o IP da ``ESP32-CAM``. Ao rodar a aplicacao, voce tem acesso ao streaming pela rota _/camera_stream_.
## Rotas
``GET /camera_stream`` 

    Retorna o streaming da camera ESP32-CAM junto com as deteccoes de gatos.
