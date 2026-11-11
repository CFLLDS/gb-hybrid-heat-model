"""Household timing diversity (review, 9 Nov 2026, P0: "run an explicit scenario with household-level diversity in
heating schedules, DHW events, occupancy, thermostat behaviour"). Inert unless called; the main runs never call it.

The main model holds every home at its set point all day and makes hot water in the same two windows (06:00-08:00,
17:30-19:30) in every home, so its homes are smooth and synchronised (coincidence factor 1.00 for 34 homes, against
0.27 measured in Freedom). Here each home gets its own habits, fixed across days:

  heating   continuous (set point all day) with probability P_CONT; otherwise two periods, as SAP's weekday pattern
            (07:00-09:00, 16:00-23:00) but with each home's own times: morning start 05:30-07:30 lasting 1.5-3 h,
            evening start 15:30-18:00, end 22:00-23:30. Off-periods hold a setback SETBACK K below the set point.
  thermal   one node per home (UA, C from the stock, as the pre-heating model); heat each half-hour is what holds or
            restores the target, limited to what the heat pump can make after any hot water, so a home recovering
            from setback runs at capacity until it is back. Days are periodic: the day is run twice and the second
            pass kept, so midnight starts from the temperature the schedule leaves.
  hot water one reheat a day at the heat pump's capacity until the day's hot water is made, starting overnight
            (01:00-05:00) in half the homes and mid-morning (07:00-10:00) in the rest.

All times are uniform draws; the shares and windows are assumptions for a sensitivity, not survey estimates.

Measured habits (library): instead of the drawn schedule, each model home is matched to one IDEAL home (Edinburgh
and the Lothians, 2016-18; scripts/spark/ideal_gas.py) and each day takes one of that home's measured winter days,
with heating ON wherever the boiler's central-heating flow pipe was above 35 C.
"""
import jax
import jax.numpy as jnp

DT = 0.5


def habits(key, B, p_cont):
    k = jax.random.split(key, 7)
    cont = jax.random.uniform(k[0], (B,)) < p_cont
    m0 = jax.random.randint(k[1], (B,), 11, 16)            # 05:30 .. 07:30
    m1 = m0 + jax.random.randint(k[2], (B,), 3, 7)          # 1.5 .. 3 h
    e0 = jax.random.randint(k[3], (B,), 31, 37)             # 15:30 .. 18:00
    e1 = jax.random.randint(k[4], (B,), 44, 48)             # 22:00 .. 23:30
    night = jax.random.uniform(k[5], (B,)) < 0.5
    d0 = jnp.where(night, jax.random.randint(k[6], (B,), 2, 11), jax.random.randint(jax.random.fold_in(k[6], 1), (B,), 14, 21))
    s = jnp.arange(48)[None, :]
    on = cont[:, None] | ((s >= m0[:, None]) & (s < m1[:, None])) | ((s >= e0[:, None]) & (s < e1[:, None]))
    return on, d0


def library_on(key, B, lib, u_day, a=None):
    """lib: dict(on (N, 48) bool sorted by home, start (H,), count (H,)). Model home -> one library home (fixed by
    key); u_day (B,) uniform picks that home's day."""
    if a is None:
        a = jax.random.randint(key, (B,), 0, lib["start"].shape[0])
    i = lib["start"][a] + jnp.floor(u_day * lib["count"][a]).astype(jnp.int32)
    return lib["on"][i]


def scheduled_demand(key, h, out, gains_w, cap, p_cont=0.4, setback=3.0, lib=None, u_day=None, a=None):
    """Returns q_space, q_dhw (B, 48) kWh per half-hour under each home's habits. cap: (B, 48) kWh per half-hour."""
    B = out.shape[0]
    if key is None:                               # national runs: hot-water start drawn from the home's fixed draw
        key = jax.random.PRNGKey(5150)
    on, d0 = habits(key, B, p_cont)
    if lib is not None:
        on = library_on(jax.random.fold_in(key, 77), B, lib, u_day, a)
    ua = h["ua"] / 1000.                                     # kW/K
    c = h["c_kwh"]                                           # kWh/K
    s = jnp.arange(48)[None, :]
    # hot water: the day's energy at capacity from the start slot
    need = h["dhw"][:, None]
    cum_cap = jnp.cumsum(jnp.where(s >= d0[:, None], cap, 0.), axis=1)
    q_dhw = jnp.clip(need - (cum_cap - jnp.where(s >= d0[:, None], cap, 0.)), 0., None)
    q_dhw = jnp.where(s >= d0[:, None], jnp.minimum(q_dhw, cap), 0.)
    room = jnp.maximum(cap - q_dhw, 0.)
    target = jnp.where(on, h["tset"][:, None], h["tset"][:, None] - setback)
    g = gains_w / 1000. * DT

    def slot(tin, i):
        t_out, tgt, gi, rm = out[:, i], target[:, i], g[:, i], room[:, i]
        want = ua * (tgt - t_out) * DT - gi + c * (tgt - tin)
        q = jnp.clip(want, 0., rm)
        tin2 = tin + (q + gi - ua * (tin - t_out) * DT) / c
        return tin2, q

    tin0 = h["tset"] - jnp.where(on[:, 0], 0., setback)
    tin, _ = jax.lax.scan(slot, tin0, jnp.arange(48))
    _, qs = jax.lax.scan(slot, tin, jnp.arange(48))
    return qs.T, q_dhw
