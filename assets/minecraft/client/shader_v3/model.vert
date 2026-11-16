#version 400 core
#extension GL_ARB_separate_shader_objects : enable

uniform mat4 u_mvp_matrix;
uniform mat4 u_ModelViewMatrix;
uniform mat4 u_ModelMatrix;
uniform vec3 u_CameraPosition;

layout (location = 0) in vec3 i_Position;
layout (location = 1) in vec2 i_TextureCoord;
layout (location = 2) in vec3 i_Normal;

layout (location = 0) out vec2 o_TextureCoord;
layout (location = 1) out vec3 o_Normal;
layout (location = 2) out vec3 o_FragmentPosition;
layout (location = 3) out vec3 o_ViewDirection;

void main() {
    gl_Position = u_mvp_matrix * vec4(i_Position, 1.0);
    o_TextureCoord = i_TextureCoord;

    o_Normal = mat3(transpose(inverse(u_ModelMatrix))) * i_Normal;
    o_FragmentPosition = vec3(u_ModelViewMatrix * vec4(gl_Position.xyz, 1.0));
    o_ViewDirection = u_CameraPosition - (u_ModelMatrix * vec4(i_Position, 1.0)).xyz;
}