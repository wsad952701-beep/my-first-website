/**
 * FLUID PARALLAX - Three.js Implementation
 * Inspired by Active Theory
 * 
 * Features:
 * - Organic fluid background using noise-based shaders
 * - Scroll-driven camera movement
 * - Mouse parallax for depth
 * - Floating 3D particles
 */

// ========================================
// SHADER CODE
// ========================================

const vertexShader = `
    varying vec2 vUv;
    varying vec3 vPosition;
    
    void main() {
        vUv = uv;
        vPosition = position;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
`;

const fragmentShader = `
    uniform float uTime;
    uniform vec2 uMouse;
    uniform vec2 uResolution;
    uniform float uScrollProgress;
    
    varying vec2 vUv;
    varying vec3 vPosition;
    
    // Simplex 3D Noise
    vec4 permute(vec4 x) { return mod(((x*34.0)+1.0)*x, 289.0); }
    vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }
    
    float snoise(vec3 v) { 
        const vec2 C = vec2(1.0/6.0, 1.0/3.0);
        const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
        
        vec3 i  = floor(v + dot(v, C.yyy));
        vec3 x0 = v - i + dot(i, C.xxx);
        
        vec3 g = step(x0.yzx, x0.xyz);
        vec3 l = 1.0 - g;
        vec3 i1 = min(g.xyz, l.zxy);
        vec3 i2 = max(g.xyz, l.zxy);
        
        vec3 x1 = x0 - i1 + C.xxx;
        vec3 x2 = x0 - i2 + C.yyy;
        vec3 x3 = x0 - D.yyy;
        
        i = mod(i, 289.0);
        vec4 p = permute(permute(permute(
            i.z + vec4(0.0, i1.z, i2.z, 1.0))
            + i.y + vec4(0.0, i1.y, i2.y, 1.0))
            + i.x + vec4(0.0, i1.x, i2.x, 1.0));
            
        float n_ = 1.0/7.0;
        vec3 ns = n_ * D.wyz - D.xzx;
        
        vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
        
        vec4 x_ = floor(j * ns.z);
        vec4 y_ = floor(j - 7.0 * x_);
        
        vec4 x = x_ *ns.x + ns.yyyy;
        vec4 y = y_ *ns.x + ns.yyyy;
        vec4 h = 1.0 - abs(x) - abs(y);
        
        vec4 b0 = vec4(x.xy, y.xy);
        vec4 b1 = vec4(x.zw, y.zw);
        
        vec4 s0 = floor(b0)*2.0 + 1.0;
        vec4 s1 = floor(b1)*2.0 + 1.0;
        vec4 sh = -step(h, vec4(0.0));
        
        vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
        vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
        
        vec3 p0 = vec3(a0.xy, h.x);
        vec3 p1 = vec3(a0.zw, h.y);
        vec3 p2 = vec3(a1.xy, h.z);
        vec3 p3 = vec3(a1.zw, h.w);
        
        vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
        p0 *= norm.x;
        p1 *= norm.y;
        p2 *= norm.z;
        p3 *= norm.w;
        
        vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
        m = m * m;
        return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
    }
    
    void main() {
        vec2 uv = vUv;
        
        // Create flowing noise layers
        float time = uTime * 0.15;
        
        // Mouse influence
        vec2 mouseInfluence = (uMouse - 0.5) * 0.2;
        
        // Multi-octave noise for organic flow
        float noise1 = snoise(vec3(uv * 2.0 + mouseInfluence, time));
        float noise2 = snoise(vec3(uv * 4.0 - mouseInfluence * 0.5, time * 1.5 + 100.0));
        float noise3 = snoise(vec3(uv * 8.0, time * 0.8 + 200.0));
        
        float combinedNoise = noise1 * 0.5 + noise2 * 0.3 + noise3 * 0.2;
        
        // Color palette based on scroll progress
        vec3 color1 = vec3(0.486, 0.227, 0.929); // Purple #7c3aed
        vec3 color2 = vec3(0.024, 0.714, 0.831); // Cyan #06b6d4
        vec3 color3 = vec3(0.957, 0.447, 0.714); // Pink #f472b6
        vec3 color4 = vec3(0.039, 0.039, 0.059); // Dark #0a0a0f
        
        // Shift colors based on scroll
        float scrollShift = uScrollProgress * 3.14159 * 2.0;
        float colorMix1 = sin(scrollShift) * 0.5 + 0.5;
        float colorMix2 = cos(scrollShift * 0.7) * 0.5 + 0.5;
        
        // Create gradient
        vec3 gradientColor = mix(
            mix(color1, color2, colorMix1),
            mix(color3, color1, colorMix2),
            combinedNoise * 0.5 + 0.5
        );
        
        // Add glow effect
        float glow = pow(combinedNoise * 0.5 + 0.5, 2.0) * 0.3;
        gradientColor += glow;
        
        // Vignette
        vec2 vignetteUv = vUv * (1.0 - vUv.yx);
        float vignette = vignetteUv.x * vignetteUv.y * 15.0;
        vignette = pow(vignette, 0.25);
        
        // Mix with dark background
        vec3 finalColor = mix(color4, gradientColor, vignette * 0.6);
        
        // Add subtle noise grain
        float grain = (snoise(vec3(vUv * 500.0, uTime * 10.0)) * 0.5 + 0.5) * 0.03;
        finalColor += grain;
        
        gl_FragColor = vec4(finalColor, 1.0);
    }
`;

// ========================================
// MAIN APPLICATION
// ========================================

class FluidParallax {
    constructor() {
        this.canvas = document.getElementById('webgl-canvas');
        this.mouse = { x: 0.5, y: 0.5 };
        this.targetMouse = { x: 0.5, y: 0.5 };
        this.scrollProgress = 0;
        this.targetScrollProgress = 0;
        this.particles = [];

        this.init();
    }

    init() {
        // Scene setup
        this.scene = new THREE.Scene();

        // Camera
        this.camera = new THREE.PerspectiveCamera(
            75,
            window.innerWidth / window.innerHeight,
            0.1,
            1000
        );
        this.camera.position.z = 5;

        // Renderer
        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
            alpha: true
        });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

        // Create elements
        this.createBackground();
        this.createParticles();
        this.createFloatingShapes();

        // Events
        this.bindEvents();

        // Start animation
        this.animate();

        // Remove loading state
        document.body.classList.remove('loading');
    }

    createBackground() {
        const geometry = new THREE.PlaneGeometry(20, 20, 1, 1);

        this.backgroundMaterial = new THREE.ShaderMaterial({
            vertexShader,
            fragmentShader,
            uniforms: {
                uTime: { value: 0 },
                uMouse: { value: new THREE.Vector2(0.5, 0.5) },
                uResolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
                uScrollProgress: { value: 0 }
            }
        });

        const background = new THREE.Mesh(geometry, this.backgroundMaterial);
        background.position.z = -5;
        this.scene.add(background);
    }

    createParticles() {
        const particleCount = 200;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const sizes = new Float32Array(particleCount);

        for (let i = 0; i < particleCount; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 20;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 40;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 10 - 2;
            sizes[i] = Math.random() * 0.1 + 0.02;
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

        const material = new THREE.PointsMaterial({
            color: 0x06b6d4,
            size: 0.05,
            transparent: true,
            opacity: 0.6,
            blending: THREE.AdditiveBlending
        });

        this.particleSystem = new THREE.Points(geometry, material);
        this.scene.add(this.particleSystem);
    }

    createFloatingShapes() {
        this.shapes = [];
        const shapeCount = 15;

        const geometries = [
            new THREE.IcosahedronGeometry(0.3, 0),
            new THREE.OctahedronGeometry(0.25, 0),
            new THREE.TetrahedronGeometry(0.3, 0),
            new THREE.TorusGeometry(0.2, 0.08, 8, 16)
        ];

        const material = new THREE.MeshBasicMaterial({
            color: 0x7c3aed,
            wireframe: true,
            transparent: true,
            opacity: 0.4
        });

        for (let i = 0; i < shapeCount; i++) {
            const geometry = geometries[Math.floor(Math.random() * geometries.length)];
            const mesh = new THREE.Mesh(geometry, material.clone());

            mesh.position.x = (Math.random() - 0.5) * 15;
            mesh.position.y = (Math.random() - 0.5) * 30;
            mesh.position.z = (Math.random() - 0.5) * 5 - 1;

            mesh.userData = {
                rotationSpeed: {
                    x: (Math.random() - 0.5) * 0.02,
                    y: (Math.random() - 0.5) * 0.02,
                    z: (Math.random() - 0.5) * 0.02
                },
                floatOffset: Math.random() * Math.PI * 2,
                floatSpeed: Math.random() * 0.5 + 0.5,
                parallaxDepth: Math.random() * 2 + 1
            };

            this.shapes.push(mesh);
            this.scene.add(mesh);
        }
    }

    bindEvents() {
        // Resize
        window.addEventListener('resize', () => this.onResize());

        // Mouse move
        document.addEventListener('mousemove', (e) => {
            this.targetMouse.x = e.clientX / window.innerWidth;
            this.targetMouse.y = 1 - (e.clientY / window.innerHeight);
        });

        // Scroll
        window.addEventListener('scroll', () => {
            const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
            this.targetScrollProgress = window.scrollY / maxScroll;
        });
    }

    onResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.backgroundMaterial.uniforms.uResolution.value.set(
            window.innerWidth,
            window.innerHeight
        );
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        const time = performance.now() * 0.001;

        // Smooth mouse interpolation
        this.mouse.x += (this.targetMouse.x - this.mouse.x) * 0.05;
        this.mouse.y += (this.targetMouse.y - this.mouse.y) * 0.05;

        // Smooth scroll interpolation
        this.scrollProgress += (this.targetScrollProgress - this.scrollProgress) * 0.08;

        // Update shader uniforms
        this.backgroundMaterial.uniforms.uTime.value = time;
        this.backgroundMaterial.uniforms.uMouse.value.set(this.mouse.x, this.mouse.y);
        this.backgroundMaterial.uniforms.uScrollProgress.value = this.scrollProgress;

        // Camera parallax based on mouse
        this.camera.position.x = (this.mouse.x - 0.5) * 2;
        this.camera.position.y = (this.mouse.y - 0.5) * 1 - this.scrollProgress * 20;
        this.camera.lookAt(0, -this.scrollProgress * 20, 0);

        // Animate particles
        if (this.particleSystem) {
            this.particleSystem.rotation.y = time * 0.05;
            this.particleSystem.position.y = -this.scrollProgress * 20;
        }

        // Animate floating shapes
        this.shapes.forEach((shape, i) => {
            const data = shape.userData;

            // Rotation
            shape.rotation.x += data.rotationSpeed.x;
            shape.rotation.y += data.rotationSpeed.y;
            shape.rotation.z += data.rotationSpeed.z;

            // Float animation
            const floatY = Math.sin(time * data.floatSpeed + data.floatOffset) * 0.3;

            // Parallax with scroll
            const baseY = (i / this.shapes.length - 0.5) * 30;
            shape.position.y = baseY + floatY - this.scrollProgress * 20 * data.parallaxDepth;

            // Color shift based on scroll
            const hue = (this.scrollProgress + i / this.shapes.length) % 1;
            shape.material.color.setHSL(0.75 - hue * 0.3, 0.8, 0.5);
        });

        this.renderer.render(this.scene, this.camera);
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    document.body.classList.add('loading');
    new FluidParallax();
});
