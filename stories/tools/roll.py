#!/usr/bin/env python3
"""Chronicles of Darkness 2e d10 roller using OS randomness.

8+ succeeds; 10s reroll (10-again) by default. Pool <= 0 rolls a chance die
(only 10 succeeds, 1 is a dramatic failure). 5+ successes = exceptional.

  roll.py 7                     # 7 dice, 10-again
  roll.py 7 --again 9           # 9-again
  roll.py 7 --again 0           # no rerolls
  roll.py 7 --rote              # reroll each initial failure once
  roll.py 0                     # chance die
  roll.py 7 -n 3 --label Init   # three separate rolls
  roll.py --init 5              # initiative: 1d10 + 5, no explosion
"""
import argparse
import secrets


def d10():
    return secrets.randbelow(10) + 1


def roll_pool(pool, again=10, rote=False):
    if pool <= 0:
        die = d10()
        return {"chance": True, "dice": [die], "successes": int(die == 10),
                "dramatic": die == 1}
    dice, rerolls = [], []
    for _ in range(pool):
        chain = [d10()]
        if rote and chain[0] < 8:
            chain.append(d10())
        while again and chain[-1] >= again:
            chain.append(d10())
        dice.append(chain)
    # A rote-rerolled initial die is < 8, so counting every die >= 8 is correct.
    succ = sum(1 for chain in dice for d in chain if d >= 8)
    return {"chance": False, "dice": dice, "successes": succ, "dramatic": False}


def fmt(chain):
    return "→".join(str(d) for d in chain) if len(chain) > 1 else str(chain[0])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("pool", type=int, nargs="?")
    p.add_argument("--again", type=int, default=10, help="10, 9, 8, or 0 for none")
    p.add_argument("--rote", action="store_true")
    p.add_argument("-n", type=int, default=1, help="number of rolls")
    p.add_argument("--label", default="")
    p.add_argument("--init", type=int, help="initiative modifier: d10 + mod")
    a = p.parse_args()
    if a.init is not None:
        for _ in range(a.n):
            die = d10()
            print(f"{a.label} initiative: d10={die} + {a.init} = {die + a.init}")
        return
    if a.pool is None:
        p.error("pool required")
    for _ in range(a.n):
        r = roll_pool(a.pool, a.again, a.rote)
        tag = f"{a.label}: " if a.label else ""
        if r["chance"]:
            d = r["dice"][0]
            res = "SUCCESS" if r["successes"] else ("DRAMATIC FAILURE" if r["dramatic"] else "failure")
            print(f"{tag}chance die [{d}] → {res}")
        else:
            s = r["successes"]
            res = "exceptional success" if s >= 5 else ("success" if s else "failure")
            print(f"{tag}{a.pool} dice [{', '.join(fmt(c) for c in r['dice'])}] → {s} successes ({res})")


if __name__ == "__main__":
    main()
