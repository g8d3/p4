import math

def ladder(Pa, Pb, C=1.0):
    """Uniswap V3 position, range [Pa,Pb] entirely below spot. token0=risky, token1=quote(USDC).
    Returns function value(P) in quote terms, plus stats."""
    a, b = math.sqrt(Pa), math.sqrt(Pb)
    L = C / (b - a)          # liquidity such that at P=Pb the position holds exactly C quote
    def parts(P):
        if P >= Pb: return 0.0, C
        if P <= Pa: return L*(1/a - 1/b), 0.0
        return L*(1/math.sqrt(P) - 1/b), L*(math.sqrt(P) - a)
    def value(P):
        x0, x1 = parts(P)
        return x0*P + x1
    return L, parts, value

def show(Pb, Pa, label):
    L, parts, value = ladder(Pa, Pb)
    avg_entry = math.sqrt(Pa*Pb)
    print(f"--- range [{Pa:.4f}, {Pb:.4f}]  ({label})   ATH=1.00")
    print(f"    avg entry if fully filled = {avg_entry:.4f}  ({avg_entry-1:+.1%} vs ATH)")
    for P in [Pb, 0.4, 0.3, 0.2, 0.1, 0.05, 0.02, 0.01]:
        if P > Pb: continue
        x0, x1 = parts(P)
        v = value(P)
        print(f"    price {P:6.3f} ({P-1:+7.1%})  value {v:6.3f}C ({v-1:+7.1%})  risky-held {x0*x0*0+ (x0 and 1):.0f}"
              f"  tokens {x0:8.3f}  quote {x1:6.3f}")
    print()

show(0.50, 0.05, "-50% to -95%  (the proposed plan)")
show(0.50, 0.02, "-50% to -98%")
show(0.30, 0.05, "-70% to -95%")
show(0.70, 0.30, "-30% to -70%")
