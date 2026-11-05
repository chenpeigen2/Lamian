import { Component, Suspense, useEffect, useMemo, useRef, type ReactNode } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { Environment, Lightformer, OrbitControls, useGLTF } from '@react-three/drei';
import { Box3, Mesh, MeshStandardMaterial, Vector3, ACESFilmicToneMapping, PCFShadowMap } from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';

export type CameraView = 'hero' | 'top' | 'low';
export interface ViewerProps {
  rotating: boolean;
  wireframe: boolean;
  view: CameraView;
  reset: number;
  zoom: number;
  onReady: () => void;
  onError: () => void;
}
const url = `${import.meta.env.BASE_URL}media/lamian.glb`;

class ViewerBoundary extends Component<{ children: ReactNode; onError: () => void }, { error: boolean }> {
  state = { error: false };
  static getDerivedStateFromError() { return { error: true }; }
  componentDidCatch() { this.props.onError(); }
  render() { return this.state.error ? null : this.props.children; }
}

function Model({ wireframe, onReady }: Pick<ViewerProps, 'wireframe' | 'onReady'>) {
  const invalidate = useThree((s) => s.invalidate);
  const gltf = useGLTF(url);
  const model = useMemo(() => {
    const clone = gltf.scene.clone(true);
    clone.traverse((object) => {
      if (object instanceof Mesh) {
        object.material = Array.isArray(object.material)
          ? object.material.map((m) => m.clone()) : object.material.clone();
      }
    });
    const box = new Box3().setFromObject(clone);
    const center = box.getCenter(new Vector3());
    clone.position.set(-center.x, -box.min.y, -center.z);
    clone.traverse((object) => {
      if (object instanceof Mesh) {
        object.castShadow = true;
        object.receiveShadow = true;
        const materials = Array.isArray(object.material) ? object.material : [object.material];
        materials.forEach((m) => {
          // Bright room without mirror-like hotspot streaks on the glass table.
          if (m.transmission > 0.5) {
            m.envMapIntensity = 0.18;
            m.roughness = Math.max(m.roughness, 0.22);
          }
        });
      }
    });
    return clone;
  }, [gltf.scene]);
  useEffect(() => {
    model.traverse((o) => {
      if (o instanceof Mesh) {
        const materials = Array.isArray(o.material) ? o.material : [o.material];
        materials.forEach((m: MeshStandardMaterial) => { m.wireframe = wireframe; });
      }
    });
    invalidate();
  }, [model, wireframe, invalidate]);
  useEffect(() => { onReady(); }, [onReady]);
  useEffect(() => () => {
    model.traverse((o) => {
      if (o instanceof Mesh) (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => m.dispose());
    });
  }, [model]);
  return <primitive object={model} />;
}

function Camera({ view, reset, rotating, zoom }: Pick<ViewerProps, 'view' | 'reset' | 'rotating' | 'zoom'>) {
  const ref = useRef<OrbitControlsImpl>(null);
  const { camera, size, invalidate } = useThree();
  const gltf = useGLTF(url);
  const bounds = useMemo(() => new Box3().setFromObject(gltf.scene), [gltf.scene]);
  const fitPoints = useMemo(() => {
    const points: Vector3[] = [];
    gltf.scene.updateMatrixWorld(true);
    const center = bounds.getCenter(new Vector3());
    // The meal and props define the framing; the room-sized table is context, not bounds.
    const context = /Table|Lattice|Floor|Back wall|Background|Chair|Fridge|Shelf carton|Tile joint|Fine tabletop/i;
    gltf.scene.traverse((object) => {
      if (!(object instanceof Mesh) || context.test(object.name)) return;
      const position = object.geometry.getAttribute('position');
      for (let i = 0; i < position.count; i += 6) {
        points.push(new Vector3().fromBufferAttribute(position, i).applyMatrix4(object.matrixWorld).sub(center));
      }
    });
    return points;
  }, [bounds, gltf.scene]);
  const distance = useRef(0.8);
  useEffect(() => {
    const dimensions = bounds.getSize(new Vector3());
    const target = new Vector3(0, dimensions.y / 2, 0);
    const direction = (view === 'top' ? new Vector3(0, 1, .08) : view === 'low' ? new Vector3(.08, .30, 1) : new Vector3(.13, .68, 1)).normalize();
    const aspect = size.width / size.height;
    const verticalFov = 38 * Math.PI / 180;
    const tanV = Math.tan(verticalFov / 2) * .76;
    const tanH = Math.tan(verticalFov / 2) * aspect * .87;
    const right = new Vector3().crossVectors(new Vector3(0, 1, 0), direction).normalize();
    const up = new Vector3().crossVectors(direction, right).normalize();
    let fittedDistance = 0;
    // Fit sampled mesh vertices, excluding empty space between the separate objects.
    for (const corner of fitPoints) {
      fittedDistance = Math.max(fittedDistance, corner.dot(direction) + Math.max(Math.abs(corner.dot(right)) / tanH, Math.abs(corner.dot(up)) / tanV));
    }
    distance.current = fittedDistance;
    camera.position.copy(target).add(direction.normalize().multiplyScalar(distance.current));
    camera.lookAt(target);
    if (ref.current) { ref.current.target.copy(target); ref.current.update(); }
    invalidate();
  }, [bounds, fitPoints, camera, view, reset, size.width, size.height, invalidate]);
  useEffect(() => {
    if (!ref.current) return;
    const delta = camera.position.clone().sub(ref.current.target);
    camera.position.copy(ref.current.target).add(delta.normalize().multiplyScalar(distance.current * Math.pow(.82, zoom)));
    ref.current.update();
    invalidate();
  }, [camera, zoom, invalidate]);
  return <OrbitControls ref={ref} makeDefault autoRotate={rotating} autoRotateSpeed={.65} enablePan={false}
    minDistance={.29} maxDistance={4} minPolarAngle={.05} maxPolarAngle={Math.PI / 2 - .035} enableDamping dampingFactor={.075} />;
}

function AutoRotateTick({ active }: { active: boolean }) {
  const invalidate = useThree((s) => s.invalidate);
  useEffect(() => {
    if (!active) return;
    let raf = 0;
    const loop = () => { invalidate(); raf = requestAnimationFrame(loop); };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [active, invalidate]);
  return null;
}

export default function Viewer(props: ViewerProps) {
  return <ViewerBoundary onError={props.onError}>
    <Canvas frameloop="demand" shadows dpr={[1, 1.3]} camera={{ fov: 38, near: .005, far: 30, position: [.1, .55, .75] }}
      gl={{ antialias: true, alpha: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' }}
      onCreated={({ gl, scene }) => { gl.toneMapping = ACESFilmicToneMapping; gl.toneMappingExposure = 1.25; gl.shadowMap.type = PCFShadowMap; (window as unknown as { __lamianDebug?: unknown }).__lamianDebug = { scene, gl }; }}>
      <color attach="background" args={['#efe7db']} />
      <fog attach="fog" args={['#efe7db', 1.6, 4.5]} />
      <mesh receiveShadow position={[0, -0.002, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[40, 40]} />
        <meshStandardMaterial color="#e3d8c6" roughness={0.95} />
      </mesh>
      <ambientLight intensity={0.9} color="#fff2e0" />
      <directionalLight position={[-1.6, 2.6, 2.2]} intensity={2.8} color="#fff1da" castShadow
        shadow-mapSize-width={1024} shadow-mapSize-height={1024} shadow-bias={-0.0004} shadow-normalBias={0.012}
        shadow-camera-near={.4} shadow-camera-far={7} shadow-camera-left={-1.4} shadow-camera-right={1.4}
        shadow-camera-top={1.6} shadow-camera-bottom={-1.2} />
      <directionalLight position={[2.4, 1.8, 1.2]} intensity={1.4} color="#ffffff" />
      <directionalLight position={[2.4, 1.4, -1.8]} intensity={0.7} color="#d9e4ff" />
      <Environment resolution={256}>
        <Lightformer form="rect" intensity={3.2} color="#fff2df" position={[-1.5, 2.5, 1.5]} scale={[4, 2, 1]} />
        <Lightformer form="rect" intensity={3.2} color="#ffffff" position={[0, 2.2, 0]} rotation={[Math.PI / 2, 0, 0]} scale={[2.5, .35, 1]} />
        <Lightformer form="rect" intensity={1.6} color="#dfe8ff" position={[2.5, 1, -2]} scale={[3, 3, 1]} />
      </Environment>
      <Suspense fallback={null}><Model wireframe={props.wireframe} onReady={props.onReady} /><Camera {...props} /><AutoRotateTick active={props.rotating} /></Suspense>
    </Canvas>
  </ViewerBoundary>;
}
