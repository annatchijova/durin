"use client";

import { useEffect, useRef } from "react";

type Star = { x: number; y: number; r: number; tw: number; sp: number };
type Shooter = { x: number; y: number; vx: number; vy: number; life: number };
type Plankton = { x: number; y: number; vx: number; vy: number; r: number; life: number; decay: number; hue: number };
type Ripple = { x: number; y: number; r: number; life: number };

/**
 * The night sea from Desktop/el_mar_de_noche.html, ported whole as the
 * landing's backdrop: sky gradient, twinkling stars, an occasional shooting
 * star, the moon and its shimmer on the water, slow wave lines, ripples on
 * press, and bioluminescent plankton stirred by the pointer below the
 * horizon. Only the original's text layer (title, whispers, hint, button)
 * was left out. Pointer events are read on the window so the content
 * sitting above the canvas does not shadow the water.
 */
export function NightSeaCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let W = 0;
    let H = 0;
    let HORIZON = 0;
    let frame = 0;
    let t = 0;
    const stars: Star[] = [];
    const plankton: Plankton[] = [];
    const ripples: Ripple[] = [];
    let shooter: Shooter | null = null;
    const moon = { x: 0, y: 0 };
    let lastX: number | null = null;
    let lastY: number | null = null;
    const timers: number[] = [];

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = window.innerWidth;
      H = window.innerHeight;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      canvas.style.width = `${W}px`;
      canvas.style.height = `${H}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      HORIZON = H * 0.42;
      moon.x = W * 0.72;
      moon.y = HORIZON * 0.5;
      if (stars.length === 0) {
        for (let i = 0; i < 160; i++) {
          stars.push({ x: Math.random() * W, y: Math.random() * HORIZON * 0.95, r: Math.random() * 1.2 + 0.2, tw: Math.random() * 6.28, sp: Math.random() * 0.03 + 0.005 });
        }
      }
    };

    const stir = (x: number, y: number, strength = 3) => {
      if (y < HORIZON) return;
      for (let i = 0; i < strength; i++) {
        plankton.push({
          x: x + (Math.random() - 0.5) * 24,
          y: y + (Math.random() - 0.5) * 18,
          vx: (Math.random() - 0.5) * 0.8,
          vy: -(Math.random() * 0.6 + 0.1),
          r: Math.random() * 2.2 + 0.8,
          life: 1,
          decay: Math.random() * 0.008 + 0.004,
          hue: 170 + Math.random() * 60,
        });
      }
    };

    const onMove = (e: PointerEvent) => {
      if (lastX !== null && lastY !== null) {
        const d = Math.hypot(e.clientX - lastX, e.clientY - lastY);
        stir(e.clientX, e.clientY, Math.min(6, Math.floor(1 + d * 0.15)));
      }
      lastX = e.clientX;
      lastY = e.clientY;
    };
    const onDown = (e: PointerEvent) => {
      if (e.clientY < HORIZON) return;
      stir(e.clientX, e.clientY, 30);
      ripples.push({ x: e.clientX, y: e.clientY, r: 0, life: 1 });
    };

    const drawFrame = () => {
      t += 0.016;
      const sky = ctx.createLinearGradient(0, 0, 0, HORIZON);
      sky.addColorStop(0, "#03040f");
      sky.addColorStop(0.6, "#0a1430");
      sky.addColorStop(1, "#16294d");
      ctx.fillStyle = sky;
      ctx.fillRect(0, 0, W, HORIZON);

      for (const s of stars) {
        s.tw += s.sp;
        ctx.globalAlpha = 0.4 + Math.sin(s.tw) * 0.4;
        ctx.fillStyle = "#fff";
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, 6.28);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      if (!shooter && Math.random() < 0.004) {
        shooter = { x: Math.random() * W * 0.6, y: Math.random() * HORIZON * 0.5, vx: 6 + Math.random() * 4, vy: 2 + Math.random() * 2, life: 1 };
      }
      if (shooter) {
        shooter.x += shooter.vx;
        shooter.y += shooter.vy;
        shooter.life -= 0.02;
        ctx.strokeStyle = `rgba(255,255,255,${shooter.life})`;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(shooter.x, shooter.y);
        ctx.lineTo(shooter.x - shooter.vx * 6, shooter.y - shooter.vy * 6);
        ctx.stroke();
        if (shooter.life <= 0 || shooter.x > W) shooter = null;
      }

      const mg = ctx.createRadialGradient(moon.x, moon.y, 0, moon.x, moon.y, 110);
      mg.addColorStop(0, "rgba(230,240,255,0.95)");
      mg.addColorStop(0.25, "rgba(200,220,255,0.4)");
      mg.addColorStop(1, "rgba(200,220,255,0)");
      ctx.fillStyle = mg;
      ctx.beginPath();
      ctx.arc(moon.x, moon.y, 110, 0, 6.28);
      ctx.fill();
      ctx.fillStyle = "#eef4ff";
      ctx.beginPath();
      ctx.arc(moon.x, moon.y, 26, 0, 6.28);
      ctx.fill();

      const sea = ctx.createLinearGradient(0, HORIZON, 0, H);
      sea.addColorStop(0, "#0c2440");
      sea.addColorStop(0.5, "#071a30");
      sea.addColorStop(1, "#030c18");
      ctx.fillStyle = sea;
      ctx.fillRect(0, HORIZON, W, H - HORIZON);

      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      for (let i = 0; i < 26; i++) {
        const yy = HORIZON + i * ((H - HORIZON) / 26);
        const w = 8 + i * 2.2;
        const shimmer = Math.sin(t * 2 + i * 0.6) * 6;
        ctx.globalAlpha = 0.06 * (1 - i / 30);
        ctx.fillStyle = "#cfe4ff";
        ctx.fillRect(moon.x - w / 2 + shimmer, yy, w, 3);
      }
      ctx.restore();

      ctx.strokeStyle = "rgba(120,170,220,0.08)";
      ctx.lineWidth = 1;
      for (let k = 0; k < 7; k++) {
        const yBase = HORIZON + ((H - HORIZON) * (k + 1)) / 8;
        ctx.beginPath();
        for (let x = 0; x <= W; x += 12) {
          const y = yBase + Math.sin(x * 0.02 + t * 1.5 + k) * 3;
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      for (let i = ripples.length - 1; i >= 0; i--) {
        const r = ripples[i];
        r.r += 2.2;
        r.life -= 0.02;
        if (r.life <= 0) {
          ripples.splice(i, 1);
          continue;
        }
        ctx.globalAlpha = r.life * 0.4;
        ctx.strokeStyle = "#9fd4ff";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.ellipse(r.x, r.y, r.r, r.r * 0.35, 0, 0, 6.28);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;

      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      for (let i = plankton.length - 1; i >= 0; i--) {
        const p = plankton[i];
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.006;
        p.life -= p.decay;
        if (p.life <= 0) {
          plankton.splice(i, 1);
          continue;
        }
        const glow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 6);
        glow.addColorStop(0, `hsla(${p.hue},90%,70%,${p.life})`);
        glow.addColorStop(1, `hsla(${p.hue},90%,60%,0)`);
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r * 6, 0, 6.28);
        ctx.fill();
        ctx.fillStyle = `hsla(${p.hue},100%,90%,${p.life})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r * 0.6, 0, 6.28);
        ctx.fill();
      }
      ctx.restore();
    };

    const loop = () => {
      drawFrame();
      frame = requestAnimationFrame(loop);
    };

    resize();
    window.addEventListener("resize", resize);
    if (reduced) {
      // One still frame with a little life on the water; no animation loop.
      for (let x = W * 0.3; x < W * 0.7; x += 20) stir(x, HORIZON + (H - HORIZON) * 0.5, 3);
      drawFrame();
    } else {
      window.addEventListener("pointermove", onMove);
      window.addEventListener("pointerdown", onDown);
      timers.push(
        window.setTimeout(() => {
          for (let x = W * 0.3; x < W * 0.7; x += 20) timers.push(window.setTimeout(() => stir(x, HORIZON + (H - HORIZON) * 0.5, 3), (x - W * 0.3) * 1.5));
        }, 1600),
      );
      frame = requestAnimationFrame(loop);
    }

    return () => {
      cancelAnimationFrame(frame);
      timers.forEach((id) => window.clearTimeout(id));
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerdown", onDown);
    };
  }, []);

  return <canvas ref={ref} aria-hidden="true" className="night-sea-canvas" />;
}
