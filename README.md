# 拉面参考重建

## 网页展示

技术栈：TypeScript、Vite、React、Three.js、React Three Fiber。参考 `D:/code/3d娃娃` 的 Blender → GLB → 浏览器实时查看流程。

```powershell
npm install
npm run dev
```

本机访问 `http://127.0.0.1:5186/`。开发服务监听所有网卡，同一局域网可通过本机 IP 的 5186 端口访问，需 Windows 防火墙允许。

- 默认展示可拖拽旋转、缩放的真实 GLB 模型，提供自动旋转、复位、主视角/平视/俯视、线框与全屏。
- 同页包含 3 张 Cycles 渲染图、环绕视频、4 张实拍参考和 Blender/GLB/完整工程下载。
- `npm run build` 生成静态站点 `dist/`，可部署至静态网站服务器；不支持直接双击 HTML 文件启动。
- `npm run test:e2e` 使用本机 Edge 执行 Playwright 测试，先确保开发服务在 5186 运行。
- 网页模型位于 `public/media/lamian.glb`，经 Meshopt 与 WebP 优化约 3.29 MiB，独立于原 `.blend`。
- `scripts/export_web.py` 从 Blender 导出网页模型，`npm run assets:optimize` 压缩导出的 GLB。
- 原模型贴图和材质经过浏览器兼容处理，实时效果不等同于 Cycles。网页保留了初版的真实感限制说明。

网页源代码入口：`src/App.tsx`；三维查看器：`src/Viewer.tsx`；布局：`src/style.css`。

## 打开入口

- `output/Lamian_Reconstruction.blend`：Blender 5.2.3 LTS 可编辑工程，23 张贴图已内嵌。
- `output/hero.png`：1800 × 1500 主视角。
- `output/low_angle.png`：1500 × 1100 低机位。
- `output/top_detail.png`：1400 × 1400 俯视细节。
- `output/orbit_preview.mp4`：800 × 640、12 fps、3 秒、约 75 度环绕预览，不是完整 360 度。
- `output/validation.json`：工程重载后生成的结构检查。

## 当前版本的准确定位

这是参考照片辅助的三维重建初版，不是摄影测量扫描，也尚未达到照片级逼真。照片纹理与有体积的食材模型结合，碗、瓷勺、面条、茶杯、桌面和环境为独立三维物体，可改变机位、灯光并编辑。

主要还原对象：青花瓷碗、红油汤面、5 块牛肉、蔬菜与木耳、面条、白瓷勺、烧饼盘、饮料杯、筷子、木格玻璃桌及简化餐馆背景。

## 已知差距

1. 牛肉和蔬菜是沿照片轮廓重建的薄体积模型。边缘、背面和内部纤维没有足够实拍证据，低机位仍有薄片感，不适合极近景或任意翻转观察。
2. 食材颜色保留了部分原始照片光照，因此不是彻底去光照的 PBR 扫描材质。
3. 碗内外花纹从可见照片提取并重复排列，不是精确展开的原碗整圈图案。部分图案会有拉伸。
4. 汤面的细碎食材有一部分来自颜色纹理，并非每片蛋花、每根菜丝都有独立几何。
5. 烧饼、瓷勺与环境为近似建模，尚未达到实拍中的轮廓和细节精度。
6. 碗口直径估计为 29.8 cm。素材没有标尺，所有绝对尺寸均为估计。
7. 视频仅作为参考观看和关键帧核验，没有执行 SfM、多视图稠密重建或相机求解。

## 重建与渲染

在项目根目录运行（Windows）：

```powershell
python scripts/prepare_assets.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --threads 16 --python scripts/build_scene.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background output/Lamian_Reconstruction.blend --threads 16 --python scripts/render_deliverables.py
```

`prepare_assets.py` 使用 Python 的 Pillow、NumPy 和 OpenCV。Blender 脚本不依赖额外插件。静帧使用 Cycles CPU 渲染；工程默认主视角、1800 × 1500、96 samples。渲染脚本会输出三张静帧和 36 张环绕序列，不会覆盖工程中的主视角设置。

## 工程组织

集合按瓷器、汤、牛肉、蔬菜、面条、瓷勺、烧饼、茶杯、桌面、环境、灯光和相机分类。工程包含 4 台相机；环绕相机带有跟踪碗中心的约束。材质贴图已打包，单独移动 `.blend` 仍可打开。

原始 4 张照片与约 9.67 秒视频未修改。
