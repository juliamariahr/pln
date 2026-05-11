# Chatbot de dependency parsing

Este projeto traz um chatbot simples em Python que usa o parser de dependências do spaCy para identificar quem está solicitando uma ação em frases em português.

### Pequena melhoria técnica

O detector sintático do chatbot prioriza verbos explícitos de solicitação, mas também considera alguns auxiliares modais relevantes, como `dever` e `poder`, porque certas construções em português usam essas formas para expressar pedido, obrigação ou possibilidade ligada à ação solicitada.

## Ambiente virtual

Crie e ative a `venv` no Windows PowerShell com:

```powershell
python -m venv .venv
```

## Instalação

```powershell
python -m pip install -r requirements.txt
python -m spacy download pt_core_news_sm
```

## Uso

Modo interativo:

```powershell
python chatbot_dependencia.py
```

Modo de frase única:

```powershell
python chatbot_dependencia.py --text "O gerente pediu para João enviar o relatório."
```

## Exemplo

Entrada:

```text
O gerente pediu para João enviar o relatório.
```

Saída esperada:

```text
Responsável por solicitar a ação: O gerente
Ação solicitada: enviar o relatório
Verbo detectado: pediu
```

## Exemplo com auxiliar modal

Entrada:

```text
O gerente deve solicitar o relatório.
```

Saída esperada:

```text
Responsável por solicitar a ação: O gerente
Ação solicitada: solicitar o relatório.
Verbo detectado: deve
```