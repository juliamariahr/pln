# PC.23 - Reconhecimento de fala em ingles

Este projeto faz transcricao de fala em **lingua inglesa** (`en-US`) a partir de **arquivo de audio**.

## 1. Objetivo

Construir um programa que:
- le um arquivo de audio,
- faz reconhecimento de fala,
- imprime a transcricao para ser consumida por um sistema de PLN.

## 2. Bibliotecas usadas

- `SpeechRecognition`

O projeto foi mantido somente em modo arquivo para evitar problemas de instalacao com `PyAudio` no Windows.

## 3. Instalacao

No terminal, dentro da pasta `pc23`:

```bash
pip install -r requirements.txt
```

## 4. Execucao

```bash
python pc23.py --audio sample.wav
```

Formatos suportados pelo `SpeechRecognition` via `AudioFile`: `wav`, `aiff`, `flac`.

## 5. Casos problematicos para PLN

Abaixo, dois cenarios em que a transcricao automatica pode gerar saida problematica para um pipeline de PLN.

### Caso A - Homofonos e pontuacao ausente

- Fala esperada: `Let's eat, Grandma.`
- Possivel transcricao ASR: `lets eat grandma`

Problema para PLN:
- perda de pontuacao altera o sentido semantico,
- tokenizacao e analise sintatica podem interpretar uma sentenca ofensiva/errada,
- tarefas de classificacao (ex.: toxicidade) podem receber falso positivo.

### Caso B - Entidades nomeadas reconhecidas incorretamente

- Fala esperada: `I transferred money to Jon at Citi.`
- Possivel transcricao ASR: `i transferred money to john at city`

Problema para PLN:
- `Jon` e `John` podem referir pessoas distintas,
- `Citi` (organizacao) vira `city` (substantivo comum),
- NER e sistemas transacionais podem mapear entidade errada.

## 6. Observacoes

- O metodo `recognize_google` usa servico online, entao depende de internet.
- Audio com ruido, baixa qualidade ou muita sobreposicao de fala tende a piorar a transcricao.
- Em producao, convem adicionar pos-processamento (pontuacao, normalizacao e validacao de entidades).
