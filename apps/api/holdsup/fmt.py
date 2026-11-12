"""Numbers as code writes them for readers: in explanations, reasons and notes."""


def fmt(x: float) -> str:
    """A readable figure: 28135.6 → '28,136'; 28.0937 → '28.1'; 0.5214 → '0.52'."""
    size = abs(x)
    if size >= 1000:
        text = f"{x:,.0f}"
    elif size >= 10:
        text = f"{x:.1f}"
    else:
        text = f"{x:.2f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text
