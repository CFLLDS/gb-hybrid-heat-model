"""Who makes the heat, each half-hour: the controllers compared in the article.

  gas          all gas (condensing boiler, efficiency eta)
  hp           all heat pump; demand beyond capacity is charged at COP 1 (direct electric)
  biv<T>       hybrid, FIXED bivalent switch: heat pump when outside >= T C, else boiler (today's hardware default)
  ccop         hybrid, C-COP (software): heat pump when gas_p/eta > elec_p/COP, i.e. heat per penny is better
  ccop_c<L>    hybrid, carbon-aware C-COP: (gas_p + L*kg_gas)/eta > (elec_p + L*g_elec/1000)/COP, L in p/kg CO2
  ccop_nopeak  C-COP with the heat pump off 16:00-19:00 every day (v1 "network peak relief")
  sdp          SD-Power dispatch: C-COP, but a random fraction phi of homes use gas in half-hours where GB total
               demand would exceed the cap (phi from pass 1, gb_sdp_phi.py)
Any hybrid is capacity-limited: when the heat pump is chosen but cannot meet the demand, the boiler tops up.
Every home that keeps a boiler pays the gas standing charge every day.
"""
import jax
import jax.numpy as jnp

from . import cfg

METRICS = ["cost_p", "kg", "elec_kwh", "gas_kwh", "boiler_heat_kwh", "unmet_kwh", "peak_elec_kwh"]


def _use_masks(cop, out, pr, gas_p, eta, carb, shed, peak):
    e = eta[:, None]
    ccop = (gas_p / e) > (pr / cop)
    masks = [out >= t for t in cfg.BIVALENT] + [ccop]
    masks += [((gas_p + lam * cfg.GAS_KG) / e) > ((pr + lam * carb / 1000.) / cop) for lam in cfg.LAMBDA]
    masks += [ccop & ~peak[None, :], ccop & ~shed]
    return masks


def run_controllers(q, cop, cap, eta, out, prices, gas_ps, carb, phi, u, peak, cap_hyb=None):
    """q, cop, cap, out, carb, u: (B, 48); eta (B,); prices, phi (T, B, 48); gas_ps (T,); peak (48,) bool.
    u is each home's uniform draw per slot; under sdp a home sheds to gas when u < phi.
    cap_hyb: the hybrids' heat-pump capacity (B, 48) if smaller than the all-electric unit (cfg.HYB_SIZE), else cap.
    Returns M (T, C, len(METRICS), B) per house-day and E (T, C, B, 48) electricity kWh per slot."""
    hp_heat = jnp.minimum(q, cap)
    hyb_heat = hp_heat if cap_hyb is None else jnp.minimum(q, cap_hyb)
    unmet = q - hp_heat
    pk = peak[None, :]

    def row(e_slots, gas_fuel, boiler_heat, unm, pr, gas_p, sc):
        cost = (e_slots * pr).sum(1) + gas_fuel * gas_p + sc
        kg = (e_slots * carb).sum(1) / 1000. + gas_fuel * cfg.GAS_KG
        return jnp.stack([cost, kg, e_slots.sum(1), gas_fuel, boiler_heat, unm, (e_slots * pk).sum(1)]), e_slots

    def one(pr, gas_p, ph):
        rows, es = [], []
        z = jnp.zeros(q.shape[0])
        r, e = row(jnp.zeros_like(q), q.sum(1) / eta, q.sum(1), z, pr, gas_p, cfg.GAS_SC)          # gas
        rows.append(r); es.append(e)
        r, e = row(hp_heat / cop + unmet, z, z, unmet.sum(1), pr, gas_p, 0.)                         # hp
        rows.append(r); es.append(e)
        for use in _use_masks(cop, out, pr, gas_p, eta, carb, u < ph, peak):                        # hybrids
            hh = jnp.where(use, hyb_heat, 0.)
            boil = (q - hh).sum(1)
            r, e = row(hh / cop, boil / eta, boil, z, pr, gas_p, cfg.GAS_SC)
            rows.append(r); es.append(e)
        return jnp.stack(rows), jnp.stack(es)

    return jax.vmap(one)(prices, gas_ps, phi)


def a2a_policies(q_space, q_dhw, carb, prices, gas_ps, cop_a, cap_a, zone, eta):
    """Air-to-air split units heat a living zone; the boiler keeps the rest and all hot water (v1 logic).
    (T, 5, B): ctrl cost, dumb cost (p incl gas SC), ctrl kg, ctrl A2A share of all heat, ctrl A2A peak kW."""
    qz = zone[:, None] * q_space
    rest = q_space - qz + q_dhw
    q = q_space + q_dhw
    peak = jnp.zeros(48, bool).at[cfg.PEAK_SLOTS[0]:cfg.PEAK_SLOTS[1]].set(True)

    def one(pr, gas_p):
        a_d = jnp.minimum(qz, cap_a)
        c_dumb = (a_d / cop_a * pr).sum(1) + ((rest + qz - a_d) / eta[:, None]).sum(1) * gas_p + cfg.GAS_SC
        use = (gas_p / eta[:, None]) / (pr / cop_a) > 1.
        a_c = jnp.where(use, jnp.minimum(qz, cap_a), 0.)
        e = a_c / cop_a
        g = (rest + qz - a_c) / eta[:, None]
        c_ctrl = (e * pr).sum(1) + g.sum(1) * gas_p + cfg.GAS_SC
        kg = (e * carb).sum(1) / 1000 + g.sum(1) * cfg.GAS_KG
        share = a_c.sum(1) / jnp.maximum(q.sum(1), 1e-9)
        pkw = (e * 2 * peak).sum(1) / peak.sum()
        return jnp.stack([c_ctrl, c_dumb, kg, share, pkw])

    return jax.vmap(one)(prices, gas_ps)
