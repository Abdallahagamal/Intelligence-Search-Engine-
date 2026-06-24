import { useEffect, useRef } from "react";

const DEFAULTS = {
  size: 90,
  ease: 0.22,
  fadeSpeed: 0.12,
};

export default function ParticleField({
  size = DEFAULTS.size,
  ease = DEFAULTS.ease,
  fadeSpeed = DEFAULTS.fadeSpeed,
  className = "",
  style,
}) {
  const glowRef = useRef(null);
  const stateRef = useRef({
    targetX: -9999,
    targetY: -9999,
    x: -9999,
    y: -9999,
    targetAlpha: 0,
    alpha: 0,
    active: false,
  });
  const rafRef = useRef(0);

  useEffect(() => {
    const el = glowRef.current;
    if (!el) return;

    const onMove = (e) => {
      const s = stateRef.current;
      if (!s.active) {
        s.x = e.clientX;
        s.y = e.clientY;
      }
      s.targetX = e.clientX;
      s.targetY = e.clientY;
      s.targetAlpha = 1;
      s.active = true;
    };

    const onLeave = () => {
      stateRef.current.targetAlpha = 0;
      stateRef.current.active = false;
    };

    const tick = () => {
      const s = stateRef.current;
      s.x += (s.targetX - s.x) * ease;
      s.y += (s.targetY - s.y) * ease;
      s.alpha += (s.targetAlpha - s.alpha) * fadeSpeed;

      el.style.transform = `translate3d(${s.x - size / 2}px, ${s.y - size / 2}px, 0)`;
      el.style.opacity = s.alpha.toFixed(3);

      rafRef.current = requestAnimationFrame(tick);
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerleave", onLeave);
    window.addEventListener("blur", onLeave);

    tick();

    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerleave", onLeave);
      window.removeEventListener("blur", onLeave);
    };
  }, [size, ease, fadeSpeed]);

  return (
    <div
      ref={glowRef}
      aria-hidden="true"
      className={className}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: size,
        height: size,
        borderRadius: "50%",
        pointerEvents: "none",
        opacity: 0,
        background:
          "radial-gradient(circle, rgba(251,146,60,0.35) 0%, rgba(249,115,22,0.18) 35%, rgba(249,115,22,0) 70%)",
        filter: "blur(8px)",
        mixBlendMode: "screen",
        willChange: "transform, opacity",
        ...style,
      }}
    />
  );
}



///////////////////////////////////////

// src/components/ParticleField.jsx
// import { useEffect, useRef } from "react";

// export default function ParticleField({ style }) {
//   const canvasRef = useRef(null);

//   useEffect(() => {
//     const canvas = canvasRef.current;
//     const ctx = canvas.getContext("2d");
//     let W, H, particles = [], raf;
//     const mouse = { x: window.innerWidth / 2, y: window.innerHeight / 2 };

//     function resize() {
//       W = canvas.width = window.innerWidth;
//       H = canvas.height = window.innerHeight;
//     }

//     function Particle() {
//       this.reset = function () {
//         this.x = Math.random() * W;
//         this.y = Math.random() * H;
//         this.r = Math.random() * 1.4 + 0.3;
//         this.vx = (Math.random() - 0.5) * 0.25;
//         this.vy = (Math.random() - 0.5) * 0.25;
//         this.life = Math.random();
//         this.maxLife = 0.6 + Math.random() * 0.4;
//         this.orange = Math.random() < 0.35;
//       };
//       this.reset();
//     }

//     function initParticles() {
//       particles = [];
//       for (let i = 0; i < 90; i++) particles.push(new Particle());
//     }

//     function drawBg() {
//       ctx.fillStyle = "#080604";
//       ctx.fillRect(0, 0, W, H);

//       // center radial warm glow
//       const grd = ctx.createRadialGradient(W / 2, H * 0.52, 0, W / 2, H * 0.52, W * 0.52);
//       grd.addColorStop(0, "rgba(180,70,10,0.22)");
//       grd.addColorStop(0.4, "rgba(140,45,8,0.12)");
//       grd.addColorStop(1, "rgba(0,0,0,0)");
//       ctx.fillStyle = grd;
//       ctx.fillRect(0, 0, W, H);

//       // mouse follow glow
//       const mg = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, 180);
//       mg.addColorStop(0, "rgba(240,128,48,0.07)");
//       mg.addColorStop(1, "rgba(0,0,0,0)");
//       ctx.fillStyle = mg;
//       ctx.fillRect(0, 0, W, H);
//     }

//     function drawLines() {
//       for (let i = 0; i < particles.length; i++) {
//         for (let j = i + 1; j < particles.length; j++) {
//           const dx = particles[i].x - particles[j].x;
//           const dy = particles[i].y - particles[j].y;
//           const d = Math.sqrt(dx * dx + dy * dy);
//           if (d < 80) {
//             ctx.strokeStyle = `rgba(240,128,48,${(1 - d / 80) * 0.08})`;
//             ctx.lineWidth = 0.5;
//             ctx.beginPath();
//             ctx.moveTo(particles[i].x, particles[i].y);
//             ctx.lineTo(particles[j].x, particles[j].y);
//             ctx.stroke();
//           }
//         }
//       }
//     }

//     function animate() {
//       drawBg();
//       drawLines();
//       particles.forEach((p) => {
//         p.x += p.vx;
//         p.y += p.vy;
//         p.life += 0.004;
//         if (p.life > p.maxLife || p.x < 0 || p.x > W || p.y < 0 || p.y > H)
//           p.reset();
//         const alpha = Math.sin((p.life / p.maxLife) * Math.PI) * (p.orange ? 0.7 : 0.35);
//         ctx.beginPath();
//         ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
//         ctx.fillStyle = p.orange
//           ? `rgba(240,128,48,${alpha})`
//           : `rgba(255,255,255,${alpha})`;
//         ctx.fill();
//       });
//       raf = requestAnimationFrame(animate);
//     }

//     const onMouseMove = (e) => { mouse.x = e.clientX; mouse.y = e.clientY; };
//     const onResize = () => { resize(); initParticles(); };

//     window.addEventListener("mousemove", onMouseMove);
//     window.addEventListener("resize", onResize);

//     resize();
//     initParticles();
//     animate();

//     return () => {
//       cancelAnimationFrame(raf);
//       window.removeEventListener("mousemove", onMouseMove);
//       window.removeEventListener("resize", onResize);
//     };
//   }, []);

//   return (
//     <canvas
//       ref={canvasRef}
//       style={{
//         position: "fixed",
//         inset: 0,
//         width: "100%",
//         height: "100%",
//         pointerEvents: "none",
//         zIndex: 1,
//         ...style,
//       }}
//     />
//   );
// }
