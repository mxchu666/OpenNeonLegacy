#version 400 core
#extension GL_ARB_separate_shader_objects : enable

uniform sampler2D u_Sampler0;
uniform sampler2D u_MaskSampler0;

uniform int u_Offset;
uniform float u_GammaCorrection;
uniform vec2 u_TexelSize;
uniform bool u_LastIteration;

uniform bool u_UseStencil;
uniform sampler2D u_StencilSampler0;

in vec2 v_TexCoord;
out vec4 o_FragColor;

void main()
{
    float alpha = 1.0;

    if (u_LastIteration)
    {
        alpha = 1.0 - texture(u_MaskSampler0, v_TexCoord).a;
    }

    if (alpha <= 0.0)
        discard;
        
    if (u_UseStencil && u_LastIteration) 
    {
    	if (texture(u_StencilSampler0, v_TexCoord).a <= 0.0) 
        {
    		discard;    
        }
    }

    vec4 color = texture(u_Sampler0, v_TexCoord + vec2(-u_TexelSize.x * 2.0, 0.0) * u_Offset);
    color.rgb *= color.a;

    vec4 texture1 = texture(u_Sampler0, v_TexCoord + vec2(-u_TexelSize.x, u_TexelSize.y) * u_Offset);
    texture1.rgb *= texture1.a;
    color += texture1 * 2.0;

    vec4 texture2 = texture(u_Sampler0, v_TexCoord + vec2(0.0, u_TexelSize.y * 2.0) * u_Offset);
    texture2.rgb *= texture2.a;
    color += texture2;

    vec4 texture3 = texture(u_Sampler0, v_TexCoord + vec2(u_TexelSize.x, u_TexelSize.y) * u_Offset);
    texture3.rgb *= texture3.a;
    color += texture3 * 2.0;

    vec4 texture4 = texture(u_Sampler0, v_TexCoord + vec2(u_TexelSize.x * 2.0, 0.0) * u_Offset);
    texture4.rgb *= texture4.a;
    color += texture4;

    vec4 texture5 = texture(u_Sampler0, v_TexCoord + vec2(u_TexelSize.x, -u_TexelSize.y) * u_Offset);
    texture5.rgb *= texture5.a;
    color += texture5 * 2.0;

    vec4 texture6 = texture(u_Sampler0, v_TexCoord + vec2(0.0, -u_TexelSize.y * 2.0) * u_Offset);
    texture6.rgb *= texture6.a;
    color += texture6;

    vec4 texture7 = texture(u_Sampler0, v_TexCoord + vec2(-u_TexelSize.x, -u_TexelSize.y) * u_Offset);
    texture7.rgb *= texture7.a;
    color += texture7 * 2.0;

    vec4 outColor = color / 12.0;
    if (outColor.a <= 0.0)
        discard;

    o_FragColor = vec4(outColor.rgb / outColor.a, (outColor.a * u_GammaCorrection) * alpha);
}
