#version 400 core
#extension GL_ARB_separate_shader_objects : enable

// source || https://glslsandbox.com/e#108252.0

uniform sampler2D u_mask_sampler2;
uniform float u_time;
uniform vec2 u_texel_size;
uniform float u_opacity;

// compatibility with glslsandbox
#define gl_FragColor o_frag_color
#define resolution u_texel_size
#define time u_Time

layout (location = 0) in vec2 v_texture_coord;
layout (location = 0) out vec4 o_frag_color;

float snow(vec2 uv, float scale) {
    float w=smoothstep(20., 0., -uv.y*(scale/10.));if (w<.1)return 0.;
    uv+=u_time/scale;uv.y+=u_time*0.01/scale;uv.x+=sin(uv.y+u_time*.5)/scale;
    uv*=scale;vec2 s=floor(uv), f=fract(uv), p=vec2(0.0);float k=5., d;
    p=.5+.35*sin(11.*fract(sin((s+p+scale)*mat2(7, 3, 6, 5))*5.))-f;d=length(p);k=min(d, k);
    k=smoothstep(0., k, sin(f.x+f.y)*0.01);
    return k*w;
}

void main() {
    if (texture(u_mask_sampler2, v_texture_coord).a == 0.0)
        discard;

    vec2 uv=(gl_FragCoord.xy*2.-u_texel_size.xy)/min(u_texel_size.x, u_texel_size.y);
    vec3 finalColor=vec3(1
    );
    float c=smoothstep(1., 0.3, clamp(uv.y*.3+.9, 0., .75));
    c+=snow(uv, 30.)*.3;
    c+=snow(uv, 20.)*.5;
    c+=snow(uv, 15.)*.8;
    c+=snow(uv, 10.);
    c+=snow(uv, 8.);
    c+=snow(uv, 6.);
    c+=snow(uv, 5.);
    finalColor=(vec3(c*0.9, c*0.3, c));
    o_frag_color = vec4(finalColor, u_opacity);
}