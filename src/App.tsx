import { lazy, Suspense, useCallback, useEffect, useRef, useState, type ComponentType, type ReactNode } from 'react';
import { ArrowDownToLine, ArrowUpRight, Box, Camera, Check, ChevronLeft, ChevronRight, CircleHelp, Expand, Film, Grid2X2, Image as ImageIcon, Layers3, LoaderCircle, Maximize2, Pause, Play, RotateCcw, ScanLine, X, ZoomIn, ZoomOut } from 'lucide-react';
import type { CameraView } from './Viewer';

const Viewer = lazy(() => import('./Viewer'));
const media = (file: string) => `${import.meta.env.BASE_URL}media/${file}`;
type Mode = 'model' | 'renders' | 'video' | 'reference';
const modes: { id: Mode; label: string; icon: ComponentType<{ size?: number }> }[] = [
  { id: 'model', label: '三维模型', icon: Box }, { id: 'renders', label: '渲染图', icon: ImageIcon },
  { id: 'video', label: '环绕影像', icon: Film }, { id: 'reference', label: '实拍参考', icon: Camera },
];
const renders = [{ file: 'hero.webp', full: 'hero.webp', title: '主视角', caption: '01 / HERO VIEW' }, { file: 'close_detail.webp', full: 'close_detail.webp', title: '近景细节', caption: '02 / CLOSE DETAIL' }, { file: 'low_angle.webp', full: 'low_angle.webp', title: '低机位', caption: '03 / PORCELAIN STUDY' }, { file: 'top_detail.webp', full: 'top_detail.webp', title: '俯视细节', caption: '04 / FOOD DETAIL' }];
const references = [1, 2, 3, 4].map((n) => ({ file: `reference-${n}.webp`, full: `reference-${n}.webp`, title: `实拍 ${String(n).padStart(2, '0')}`, caption: `REFERENCE / 0${n}` }));

function Tool({ label, children, active, onClick, disabled }: { label: string; children: ReactNode; active?: boolean; onClick: () => void; disabled?: boolean }) {
  return <button className={`tool ${active ? 'is-active' : ''}`} title={label} aria-label={label} aria-pressed={active} onClick={onClick} disabled={disabled}>{children}</button>;
}

export default function App() {
  const [mode, setMode] = useState<Mode>('model');
  const [imageIndex, setImageIndex] = useState(0);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [wireframe, setWireframe] = useState(false);
  const [view, setView] = useState<CameraView>('hero');
  const [reset, setReset] = useState(0);
  const [zoom, setZoom] = useState(0);
  const [lightbox, setLightbox] = useState(false);
  const [about, setAbout] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  // 默认即沉浸模式：整页只剩三维场景；切到其他标签或点"展开档案"回到完整页面。
  const [immersive, setImmersive] = useState(true);
  const [videoError, setVideoError] = useState(false);
  const stage = useRef<HTMLElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const lastFocus = useRef<HTMLElement | null>(null);
  const collection = mode === 'reference' ? references : renders;
  const image = collection[imageIndex] ?? collection[0];
  const onReady = useCallback(() => setReady(true), []);
  const onError = useCallback(() => { setFailed(true); setReady(false); }, []);
  const selectMode = (next: Mode) => { setMode(next); setImageIndex(0); setVideoError(false); if (next !== 'model') setImmersive(false); };
  const changeImage = (delta: number) => setImageIndex((n) => (n + delta + collection.length) % collection.length);
  const resetCamera = () => { setView('hero'); setZoom(0); setReset((n) => n + 1); };
  const expand = async () => {
    try {
      if (document.fullscreenElement) {
        setImmersive(false);
        await document.exitFullscreen();
      } else {
        setImmersive(true);
        if (stage.current?.requestFullscreen) await stage.current.requestFullscreen();
      }
    } catch { setImmersive((value) => !value); }
  };
  useEffect(() => {
    const handler = () => {
      const active = Boolean(document.fullscreenElement);
      setFullscreen(active);
      if (!active) setImmersive(false);
    };
    document.addEventListener('fullscreenchange', handler);
    const key = (event: KeyboardEvent) => { if (event.key === 'Escape') setImmersive(false); };
    window.addEventListener('keydown', key);
    return () => { document.removeEventListener('fullscreenchange', handler); window.removeEventListener('keydown', key); };
  }, []);
  useEffect(() => {
    if (mode !== 'model') setImmersive(false);
  }, [mode]);
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (query.matches) setRotating(false);
  }, []);
  useEffect(() => {
    if (lightbox || about) {
      lastFocus.current = document.activeElement as HTMLElement;
      dialog.current?.showModal(); document.body.style.overflow = 'hidden';
    } else { dialog.current?.close(); document.body.style.overflow = ''; lastFocus.current?.focus(); }
    return () => { document.body.style.overflow = ''; };
  }, [lightbox, about]);
  const closeDialog = () => { setLightbox(false); setAbout(false); };

  return <div className={`app-shell ${immersive ? 'immersive' : ''}`}>
    <header className="site-header">
      <a className="wordmark" href={import.meta.env.BASE_URL} aria-label="LAMIAN 首页"><span className="brand-symbol"><Layers3 size={21} /></span>LAMIAN<span className="brand-suffix">/ 3D ARCHIVE</span></a>
      <div className="header-right"><span className="project-state"><i /> 重建档案 001</span><button className="icon-button" title="项目信息" aria-label="项目信息" onClick={() => setAbout(true)}><CircleHelp size={19} /></button><a className="download-link" href={media('lamian.glb')} download><ArrowDownToLine size={16} /><span>网页模型 GLB</span><ArrowUpRight size={14} /></a></div>
    </header>

    <div className={`immersive-bar ${immersive ? '' : 'is-hidden'}`} aria-hidden={!immersive}>
      <span className="immersive-brand"><Layers3 size={15} /> LAMIAN · 沉浸模式</span>
      <div className="immersive-actions">
        <a className="immersive-download" href={media('lamian.glb')} download aria-label="下载网页模型 GLB"><ArrowDownToLine size={15} /></a>
        <button className="immersive-exit" onClick={() => setImmersive(false)}><Grid2X2 size={14} /> 展开档案</button>
      </div>
    </div>

    <main>
      <section className="project-heading"><div><div className="eyebrow"><span>食物 · 器物 · 日常</span><span className="small-rule" /> BLENDER RECONSTRUCTION</div><h1>一碗牛肉面<span className="title-dot">。</span></h1></div><div className="project-meta"><span>青花瓷 / 红油汤 / 手拉面</span><span className="meta-secondary">4 张实拍 · 9.67 秒影像 · 精修版 v0.2</span></div></section>

      <section className={`workspace ${fullscreen ? 'workspace-expanded' : ''}`} ref={stage} aria-label="作品查看器">
        <div className="workspace-bar"><div className="tabs" role="tablist" aria-label="展示内容">{modes.map(({ id, label, icon: Icon }) => <button key={id} id={`tab-${id}`} role="tab" aria-selected={mode === id} aria-controls="viewer-content" className={mode === id ? 'selected' : ''} onClick={() => { selectMode(id); if (id !== 'model') setImmersive(false); }}><Icon size={16} /><span>{label}</span></button>)}</div><span className="file-type">{mode === 'model' ? 'GLB / REALTIME' : mode === 'video' ? 'CYCLES / MOTION' : mode === 'reference' ? 'ORIGINAL / PHOTO' : 'CYCLES / RENDER'}</span></div>

        <div className="stage" id="viewer-content" role="tabpanel" aria-labelledby={`tab-${mode}`}>
          {mode === 'model' && <>
            <div className="viewer-canvas" data-testid="model-stage">
              {!failed ? <Suspense fallback={null}><Viewer rotating={rotating} wireframe={wireframe} view={view} reset={reset} zoom={zoom} onReady={onReady} onError={onError} /></Suspense> : <img className="fallback-image" src={media('hero.webp')} alt="牛肉面 Blender 渲染预览" />}
              {!ready && !failed && <div className="loading-state" role="status"><LoaderCircle size={23} className="spin" /><span>正在载入模型</span></div>}
              {failed && <div className="fallback-notice" role="alert">三维模型暂不可用，已显示渲染图。<button onClick={() => selectMode('renders')}>查看渲染图 <ArrowUpRight size={14} /></button></div>}
            </div>
            <div className="stage-label"><span className="label-line" /><div><span className="overline">STUDY 001</span><strong>青花碗 · 牛肉面</strong></div></div>
            <div className="stage-status"><i className={ready ? 'ready-dot' : ''} />{failed ? '静帧预览' : ready ? '实时三维' : '加载中'}</div>
            <div className="stage-hint"><ScanLine size={13} /> 拖动旋转 · 滚轮缩放 · ESC 退出</div>
            <div className="model-controls"><div className="view-presets" role="group" aria-label="模型视角">{([{ id: 'hero', label: '主视角' }, { id: 'low', label: '平视' }, { id: 'top', label: '俯视' }] as const).map((v) => <button key={v.id} className={view === v.id ? 'active' : ''} onClick={() => { setView(v.id); setZoom(0); setReset((n) => n + 1); }}>{v.label}</button>)}</div><div className="toolbar"><Tool label={rotating ? '暂停旋转' : '自动旋转'} active={rotating} onClick={() => setRotating((v) => !v)} disabled={failed}>{rotating ? <Pause size={18} /> : <Play size={18} />}</Tool><Tool label="复位视角" onClick={resetCamera}><RotateCcw size={18} /></Tool><span className="toolbar-divider" /><Tool label="放大" onClick={() => setZoom((n) => Math.min(4, n + 1))}><ZoomIn size={18} /></Tool><Tool label="缩小" onClick={() => setZoom((n) => Math.max(-3, n - 1))}><ZoomOut size={18} /></Tool><span className="toolbar-divider" /><Tool label="线框模式" active={wireframe} onClick={() => setWireframe((v) => !v)} disabled={failed}><ScanLine size={18} /></Tool><Tool label={immersive ? '退出沉浸' : '沉浸模式'} active={immersive} onClick={() => void expand()}><Expand size={18} /></Tool></div></div>
          </>}
          {(mode === 'renders' || mode === 'reference') && <><img key={image.file} className="gallery-main" src={media(image.file)} alt={`${image.title}：青花瓷碗牛肉面${mode === 'reference' ? '实拍' : '三维渲染'}`} /><span className="image-counter">{String(imageIndex + 1).padStart(2, '0')} <span>/ {String(collection.length).padStart(2, '0')}</span></span><button className="image-arrow prev" title="上一张" aria-label="上一张" onClick={() => changeImage(-1)}><ChevronLeft size={24} /></button><button className="image-arrow next" title="下一张" aria-label="下一张" onClick={() => changeImage(1)}><ChevronRight size={24} /></button><div className="image-caption"><span>{image.caption}</span><strong>{image.title}</strong></div><button className="image-expand icon-button" title="放大图片" aria-label="放大图片" onClick={() => setLightbox(true)}><Maximize2 size={20} /></button></>}
          {mode === 'video' && <div className="video-stage">{videoError ? <div className="video-failed" role="alert">视频无法播放。<a href={media('orbit_preview.mp4')} download>下载视频</a></div> : <video controls playsInline loop preload="metadata" poster={media('hero.webp')} onError={() => setVideoError(true)}><source src={media('orbit_preview.mp4')} type="video/mp4" /></video>}<div className="video-tag"><Film size={14} /> 75° ORBIT / 03 SEC</div></div>}
        </div>
        <div className="workspace-footer"><span><span className="footer-dot" />{mode === 'model' ? 'Blender → glTF 2.0' : mode === 'reference' ? '实拍参考档案' : 'Blender 5.2 · Cycles'}</span><span>{mode === 'model' ? 'PBR / 23 TEXTURES' : mode === 'video' ? '800 × 640 / 12 FPS' : mode === 'reference' ? '4 PHOTOGRAPHS' : '4 CAMERA VIEWS'}</span></div>
      </section>

      <section className="asset-strip" aria-label="视角与素材"><div className="strip-title"><Grid2X2 size={17} /><span>{mode === 'reference' ? '实拍档案' : '视角档案'}</span><span className="strip-count">{mode === 'reference' ? '04' : '04'}</span></div><div className="thumbnails">{(mode === 'reference' ? references : renders).map((item, index) => <button className={`thumbnail ${((mode === 'renders' || mode === 'reference') && imageIndex === index) ? 'chosen' : ''}`} key={item.file} onClick={() => { if (mode !== 'reference') selectMode('renders'); setImageIndex(index); }}><img src={media(item.file)} alt="" loading="lazy" /><span><small>{String(index + 1).padStart(2, '0')}</small>{item.title}</span><ArrowUpRight size={14} /></button>)}</div></section>

      <section className="archive-details"><div className="archive-title"><span className="eyebrow">ABOUT THE OBJECT</span><h2>从餐桌上的一刻，<br />到可转动的日常。</h2><span className="version-tag"><i /> RECONSTRUCTION V0.2</span></div><div className="detail-column"><h3>重建记录</h3><dl><div><dt>原始素材</dt><dd>4 张照片 · 1 段视频</dd></div><div><dt>制作软件</dt><dd>Blender 5.2.3 LTS</dd></div><div><dt>碗口直径</dt><dd>约 29.8 cm <small>估计尺寸</small></dd></div><div><dt>模型类型</dt><dd>实体建模 + 照片纹理</dd></div></dl></div><div className="detail-column"><h3>版本说明</h3><p>v0.2 精修：瓷釉高光与青花晕染、牛肉色泽、红油与热气、手拉面和层叠烧饼均已重做。食材背面与厚度仍为估计，并非扫描级成品。</p><div className="detail-links"><a href={media('lamian.glb')} download>GLB 模型 <ArrowDownToLine size={14} /></a></div></div></section>
    </main>
    <footer className="site-footer"><span>LAMIAN <span> / </span> 日常的三维档案</span><span>MODELED IN BLENDER · VIEWED IN THREE.JS</span></footer>

    <dialog ref={dialog} className={about ? 'about-dialog' : 'lightbox'} onCancel={closeDialog} onClick={(event) => { if (event.target === event.currentTarget) closeDialog(); }}><button className="dialog-close icon-button" title="关闭" aria-label="关闭" onClick={closeDialog}><X size={23} /></button>{about ? <><span className="eyebrow">LAMIAN / STUDY 001</span><h2>一碗牛肉面</h2><p>依据 4 张照片和 9.67 秒视频建立的 Blender 三维场景。</p><p>网页实时模型使用适配浏览器的材质，不等同于 Cycles 离线渲染。食材仍有薄片感，未达到照片级逼真。</p><span className="packed-note"><Check size={16} /> 网页模型经 Meshopt 与 WebP 压缩</span><a className="dialog-download" href={media('lamian.glb')} download><ArrowDownToLine size={17} /> 下载网页模型 GLB</a></> : <><img src={media(image.full)} alt={image.title} /><div className="lightbox-controls"><Tool label="上一张" onClick={() => changeImage(-1)}><ChevronLeft size={22} /></Tool><span>{image.title} / {imageIndex + 1}</span><Tool label="下一张" onClick={() => changeImage(1)}><ChevronRight size={22} /></Tool></div></>}</dialog>
  </div>;
}
