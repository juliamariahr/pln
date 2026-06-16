from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Optional

import spacy
from spacy.tokens import Doc, Span, Token


REQUEST_VERBS = {
    "pedir",
    "solicitar",
    "requisitar",
    "requerer",
    "querer",
    "ordenar",
    "mandar",
    "determinar",
    "exigir",
    "encarregar",
    "incumbir",
    "cobrar",
}

REQUEST_MODAL_LEMMAS = {
    "dever",
    "poder",
}

REQUEST_TRIGGER_LEMMAS = REQUEST_VERBS | REQUEST_MODAL_LEMMAS

SUBJECT_DEPS = {
    "nsubj",
    "nsubj:pass",
    "csubj",
    "csubj:pass",
}

ACTION_DEPS = {
    "xcomp",
    "ccomp",
}

ACTION_DEPS_FALLBACK = {
    "xcomp",
    "ccomp",
    "obj",
    "obl",
    "advcl",
    "acl",
}

REQUEST_IMPERATIVE_MARKERS = {
    "vamos",
    "vamo",
}

COMMON_FIXES = {
    "sera": "será",
    "voce": "você",
    "esta": "está",
    "ate": "até",
}

MARKUP_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(slots=True)
class RequestAnalysis:
    sentence: str
    requester: Optional[str]
    action: Optional[str]
    trigger: Optional[str]


def load_nlp() -> "spacy.language.Language":
    try:
        return spacy.load("pt_core_news_sm")
    except OSError as exc:
        raise SystemExit(
            "O modelo pt_core_news_sm não está instalado. Execute: "
            "python -m spacy download pt_core_news_sm"
        ) from exc


def preprocess_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)

    words = normalized.split()
    words = [COMMON_FIXES.get(w.lower(), w) for w in words]
    normalized = " ".join(words)

    normalized = MARKUP_TAG_RE.sub(" ", normalized)
    normalized = normalized.replace("\u00a0", " ")

    return WHITESPACE_RE.sub(" ", normalized).strip()


def parse_text(nlp: "spacy.language.Language", text: str) -> Doc:
    return nlp(preprocess_text(text))


def token_span_text(token: Token) -> str:
    return token.doc[token.left_edge.i : token.right_edge.i + 1].text.strip()


def token_span_text_without_case(token: Token, allowed_cases: Iterable[str]) -> str:
    allowed_set = {item.lower() for item in allowed_cases}
    span = token.doc[token.left_edge.i : token.right_edge.i + 1]
    if len(span) > 1 and span[0].dep_ == "case" and span[0].lower_ in allowed_set:
        span = span[1:]
    return span.text.strip()


def has_case_preposition(token: Token, allowed: Iterable[str]) -> bool:
    allowed_set = {item.lower() for item in allowed}
    for child in token.children:
        if child.dep_ == "case" and child.lower_ in allowed_set:
            return True
    return False


def is_imperative_request(token: Token) -> bool:
    moods = {mood.lower() for mood in token.morph.get("Mood")}

    if "imp" in moods:
        return True

    if (
        token.dep_ == "ROOT"
        and token.pos_ == "VERB"
        and token.i == token.sent.start
    ):
        return True

    return (
        token.lemma_.lower() == "ir"
        and token.text.lower() in REQUEST_IMPERATIVE_MARKERS
    )


def looks_like_surface_command(token: Token) -> bool:
    sent = token.sent
    if token.i != sent.start:
        return False

    if any(item.pos_ in {"VERB", "AUX"} for item in sent):
        return False

    content_tokens = [item for item in sent if not item.is_punct and not item.is_space]
    if len(content_tokens) < 2:
        return False

    if not token.is_alpha:
        return False

    next_token = content_tokens[1]
    return next_token.pos_ in {"DET", "NOUN", "PROPN", "ADJ", "PRON", "NUM"} or next_token.dep_ == "det"


def extract_requester(verb: Token) -> Optional[str]:
    if looks_like_surface_command(verb):
        return "você (implícito)"

    for anchor in (verb, verb.head):
        if anchor == verb or verb.dep_ == "xcomp":
            for child in anchor.children:
                if child.dep_ == "obl:agent" and has_case_preposition(
                    child, {"por", "pela", "pelo", "pelas", "pelos"}
                ):
                    return token_span_text_without_case(
                        child, {"por", "pela", "pelo", "pelas", "pelos"}
                    )

            for child in anchor.children:
                if child.dep_ == "obl" and has_case_preposition(
                    child, {"por", "pela", "pelo", "pelas", "pelos"}
                ):
                    return token_span_text_without_case(
                        child, {"por", "pela", "pelo", "pelas", "pelos"}
                    )

            for child in anchor.children:
                if child.dep_ in SUBJECT_DEPS:
                    return token_span_text(child)

    for token in verb.sent:
        if token.pos_ in {"VERB", "AUX"}:
            for child in token.children:
                if child.dep_ in SUBJECT_DEPS:
                    return token_span_text(child)

    for token in verb.sent:
        if token.dep_ in SUBJECT_DEPS:
            return token_span_text(token)

    persons = {person.lower() for person in verb.morph.get("Person")}
    numbers = {number.lower() for number in verb.morph.get("Number")}

    if "1" in persons and "sing" in numbers:
        return "eu (implícito)"

    if "1" in persons and "plur" in numbers:
        return "nós (implícito)"

    if is_imperative_request(verb):
        return "você (implícito)"

    if (
        verb.lemma_.lower() == "ir"
        and verb.text.lower() in REQUEST_IMPERATIVE_MARKERS
    ):
        return "nós (implícito)"

    return None


def extract_action(verb: Token) -> Optional[str]:
    if looks_like_surface_command(verb):
        remainder = verb.doc[verb.i + 1 : verb.sent.end].text.strip().rstrip(".,;:!?")
        if remainder:
            return remainder
        return token_span_text(verb)

    if verb.lemma_.lower() == "ir" and verb.text.lower() in REQUEST_IMPERATIVE_MARKERS:
        remainder = verb.doc[verb.i + 1 : verb.sent.end].text.strip().rstrip(".,;:!?")
        if remainder:
            return remainder
        return token_span_text(verb)

    for child in verb.children:
        if child.dep_ in ACTION_DEPS:
            return token_span_text(child)

    if is_imperative_request(verb):
        remainder = verb.doc[verb.i + 1 : verb.sent.end].text.strip()
        if remainder:
            return remainder
        return verb.lemma_

    for child in verb.children:
        if child.dep_ in ACTION_DEPS_FALLBACK:
            return token_span_text(child)

    for descendant in verb.subtree:
        if descendant.dep_ in ACTION_DEPS_FALLBACK and descendant.head == verb:
            return token_span_text(descendant)

    return None


def find_request_verb(sent: Span) -> Optional[Token]:
    for token in sent:
        if token.pos_ in {"VERB", "AUX"} and token.lemma_.lower() in REQUEST_TRIGGER_LEMMAS:
            return token

        if token.pos_ in {"VERB", "AUX"} and is_imperative_request(token):
            return token

    first_token = sent[0]
    if looks_like_surface_command(first_token):
        return first_token

    # procura primeiro VERB raiz
    for token in sent:
        if token.dep_ == "ROOT" and token.pos_ == "VERB":
            return token

    # depois AUX raiz
    for token in sent:
        if token.dep_ == "ROOT" and token.pos_ == "AUX":
            return token

    # depois qualquer VERB
    for token in sent:
        if token.pos_ == "VERB":
            return token

    # por último AUX
    for token in sent:
        if token.pos_ == "AUX":
            return token

    return None

def get_verb_phrase(token):
    aux = [c for c in token.children if c.pos_ == "AUX"]
    if aux:
        return f"{aux[0].text} {token.text}"
    return token.text

def build_study_report(original_text: str, doc: Doc) -> str:
    lines = [
        f"Texto original: {original_text.strip()}",
        f"Texto normalizado: {doc.text}",
        "",
        "Pré-processamento e análise linguística:",
    ]

    for sent in doc.sents:
        token_parts = []
        content_tokens = []
        for token in sent:
            if token.is_space:
                continue
            token_parts.append(f"{token.text}/{token.lemma_}/{token.pos_}/{token.dep_}")
            if not token.is_stop and not token.is_punct:
                content_tokens.append(token.text)

        lines.append(f"- Sentença: {sent.text.strip()}")
        if token_parts:
            lines.append(f"  Tokens: {', '.join(token_parts)}")
        if content_tokens:
            lines.append(f"  Conteúdo sem stop words: {', '.join(content_tokens)}")

    lines.append(
        "Observação: stop words não são removidas antes do parsing, porque isso pode alterar o sentido e o papel sintático da frase."
    )
    return "\n".join(lines)


def analyze_doc(doc: Doc) -> list[RequestAnalysis]:
    analyses: list[RequestAnalysis] = []
    for sent in doc.sents:
        analysis = analyze_sentence(sent)
        if analysis.trigger is not None:
            analyses.append(analysis)
    return analyses


def analyze_sentence(sent: Span) -> RequestAnalysis:
    verb = find_request_verb(sent)
    if verb is None:
        return RequestAnalysis(sentence=sent.text.strip(), requester=None, action=None, trigger=None)

    return RequestAnalysis(
        sentence=sent.text.strip(),
        requester=extract_requester(verb),
        action=extract_action(verb),
        trigger=verb.text,
    )


def analyze_text(nlp: "spacy.language.Language", text: str) -> list[RequestAnalysis]:
    return analyze_doc(parse_text(nlp, text))


def format_analysis(analysis: RequestAnalysis) -> str:
    parts = []
    parts.append(f"Frase: {analysis.sentence}")
    if analysis.requester:
        parts.append(f"Responsável por solicitar a ação: {analysis.requester}")
    else:
        parts.append("Responsável por solicitar a ação: não identificado com segurança")
    if analysis.action:
        parts.append(f"Ação solicitada: {analysis.action}")
    if analysis.trigger:
        parts.append(f"Verbo detectado: {analysis.trigger}")
    return "\n".join(parts)


def run_chatbot() -> None:
    nlp = load_nlp()
    print("Chatbot de dependency parsing")
    print("Digite uma frase com pedido/solicitação e veja quem está solicitando a ação.")
    print("Use '!pipeline <texto>' para ver a etapa de pré-processamento e a análise linguística.")
    print("Digite 'sair' para encerrar.\n")

    while True:
        user_text = input("Você: ").strip()
        if not user_text:
            continue
        if user_text.lower() in {"sair", "exit", "quit"}:
            print("Bot: até mais.")
            break

        if user_text.lower().startswith("!pipeline ") or user_text.lower().startswith("!estudar "):
            raw_text = user_text.split(" ", 1)[1].strip()
            if not raw_text:
                print("Bot: informe um texto depois do comando !pipeline.")
                continue

            doc = parse_text(nlp, raw_text)
            print("Bot:")
            print(build_study_report(raw_text, doc))
            print()

            analyses = analyze_doc(doc)
            if analyses:
                for analysis in analyses:
                    print("Bot:")
                    print(format_analysis(analysis))
                    print()
            else:
                print("Bot: não encontrei um verbo de solicitação na frase.")
            continue

        analyses = analyze_text(nlp, user_text)
        if not analyses:
            print("Bot: não encontrei um verbo de solicitação na frase.")
            continue

        for analysis in analyses:
            print("Bot:")
            print(format_analysis(analysis))
            print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Chatbot simples com dependency parsing em português.")
    parser.add_argument(
        "--text",
        help="Analisa uma frase única e encerra depois.",
    )
    parser.add_argument(
        "--study",
        action="store_true",
        help="Mostra a etapa de pré-processamento antes da resposta do chatbot.",
    )
    args = parser.parse_args()

    nlp = load_nlp()
    if args.text:
        if args.study:
            doc = parse_text(nlp, args.text)
            print(build_study_report(args.text, doc))
            print()
            analyses = analyze_doc(doc)
        else:
            analyses = analyze_text(nlp, args.text)
        if not analyses:
            print("Não encontrei um verbo de solicitação na frase.")
            return
        for analysis in analyses:
            print(format_analysis(analysis))
            print()
        return

    run_chatbot()


if __name__ == "__main__":
    main()