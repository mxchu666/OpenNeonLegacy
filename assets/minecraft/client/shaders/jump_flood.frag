#version 330 core

#define DEPTH_COLOR 1

uniform sampler2D u_MaskSampler0;
uniform sampler2D u_JfaSampler2;

#if DEPTH_COLOR
uniform sampler2D u_SceneDepthSampler3;
uniform sampler2D u_DepthSampler4;
uniform bool u_UseDepth;
uniform vec4 u_OccludedColor;
uniform vec4 u_VisibleColor;
#endif

uniform vec2 u_TexelSize;
uniform float u_OutlineWidth;

uniform bool u_DoMarch;
uniform float u_MarchSteps;
uniform bool u_UseBezier;
uniform float[100] u_BezierSteps;

uniform sampler2D u_PerlinSampler5;
uniform bool u_UseFadingColors;
uniform float u_Time;
uniform vec4 u_FadingColor;

in vec2 v_TexCoord;
out vec4 o_FragColor;

vec4 outline(in vec2 texCoord, in float outlineWidth) {
    vec2 closestSeed = texture(u_JfaSampler2, texCoord).xy;
    float distance = length(closestSeed / u_TexelSize - texCoord / u_TexelSize);

    if (closestSeed.x > 0 && closestSeed.y > 0) {
        float maxAlpha = (outlineWidth - distance + 1.0);
        float result = min(maxAlpha, 1);

        if (u_UseBezier) {
            float progress = distance / outlineWidth;
            int progressIndex = clamp(int(progress * 99), 0, 99);
            float step = u_BezierSteps[progressIndex];

            result *= step;
        }

        if (result > 0) {
            vec4 color = texture(u_MaskSampler0, texCoord);

            if (color.a > 0) {
                return vec4(0.0);
            }

            #if DEPTH_COLOR
            if (u_UseDepth) {
                float sceneDepth = texture(u_SceneDepthSampler3, closestSeed).r;
                float selfDepth = texture(u_DepthSampler4, closestSeed).r;
                bool occluded = selfDepth > sceneDepth;

                vec3 color1;

                if (occluded) {
                    color1 = u_OccludedColor.rgb;
                } else {
                    color1 = u_VisibleColor.rgb;
                }

                return vec4(color1, result);
            }
            #endif

            vec4 maskColor = texture(u_MaskSampler0, closestSeed);
            return vec4(maskColor.rgb, result);
        }
    }

    return vec4(0.0);
}

vec4 march(in vec2 texCoord, in float outlineWidth, in float steps) {
    vec2 closestSeed = texture(u_JfaSampler2, texCoord).xy;
    float distance = length(closestSeed / u_TexelSize - texCoord / u_TexelSize);

    if (closestSeed.x > 0 && closestSeed.y > 0) {
        float maxAlpha = (outlineWidth - distance + 1.0);
        float progress = distance / outlineWidth;
        float evaluated = (sin(progress * outlineWidth * steps) + 1.0) / 2.0;

        float result = evaluated * min(maxAlpha, 1);

        if (result > 0) {
            vec4 color = texture(u_MaskSampler0, texCoord);

            if (color.a > 0) {
                return vec4(0.0);
            }

            vec4 maskColor = texture(u_MaskSampler0, closestSeed);

            return vec4(maskColor.rgb, result);
        }
    }

    return vec4(0.0);
}

void main() {
    vec4 color;

    if (u_DoMarch) {
        color = march(v_TexCoord, u_OutlineWidth, u_MarchSteps);
    } else {
        color = outline(v_TexCoord, u_OutlineWidth);
    }

    if (color.a <= 0.0) {
        discard;
    }

    if (u_UseFadingColors) {
        float perlin = texture(u_PerlinSampler5, fract(v_TexCoord * 0.2 + vec2(u_Time))).r;

        color.rgb = mix(u_FadingColor.rgb, color.rgb, perlin);
    }

    o_FragColor = color;
}