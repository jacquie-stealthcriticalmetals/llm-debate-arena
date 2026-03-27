AGREEMENT_SIGNALS = [
    "i agree",
    "i concur",
    "no further objections",
    "we have reached",
    "consensus",
    "i accept",
    "nothing to add",
    "fully aligned",
    "in agreement",
]


def check_consensus(responses: list[str]) -> bool:
    if len(responses) < 2:
        return False

    for resp in responses:
        tag_agree = "[AGREE]" in resp
        tail = resp[-500:].lower()
        text_agree = any(signal in tail for signal in AGREEMENT_SIGNALS)
        if not (tag_agree or text_agree):
            return False
    return True
