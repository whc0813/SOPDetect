<template>
  <div class="ambient-blobs" aria-hidden="true">
    <div class="blob blob-blue"></div>
    <div class="blob blob-purple"></div>
    <div class="blob blob-green"></div>
  </div>
</template>

<style scoped>
.ambient-blobs {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(72px);
}

.blob-blue {
  width: 560px;
  height: 560px;
  top: -120px;
  left: -80px;
  background: radial-gradient(circle, rgba(0, 122, 255, 0.16) 0%, transparent 70%);
  animation: float-a 10s ease-in-out infinite alternate;
}

.blob-purple {
  width: 480px;
  height: 480px;
  bottom: -100px;
  right: -60px;
  background: radial-gradient(circle, rgba(88, 86, 214, 0.11) 0%, transparent 70%);
  animation: float-b 13s ease-in-out infinite alternate;
}

.blob-green {
  width: 360px;
  height: 360px;
  top: 10%;
  right: 20%;
  background: radial-gradient(circle, rgba(52, 199, 89, 0.08) 0%, transparent 70%);
  animation: float-c 16s ease-in-out infinite alternate;
}

@keyframes float-a {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(40px, 30px) scale(1.08); }
}

@keyframes float-b {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(-30px, -40px) scale(1.06); }
}

@keyframes float-c {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(20px, -25px) scale(1.04); }
}

@media (prefers-reduced-motion: reduce) {
  .blob { animation: none; }
}

@media (prefers-color-scheme: dark) {
  .blob-blue {
    background: radial-gradient(circle, rgba(10, 132, 255, 0.12) 0%, transparent 70%);
  }
  .blob-purple {
    background: radial-gradient(circle, rgba(94, 92, 230, 0.09) 0%, transparent 70%);
  }
  .blob-green {
    background: radial-gradient(circle, rgba(48, 209, 88, 0.06) 0%, transparent 70%);
  }
}
</style>
