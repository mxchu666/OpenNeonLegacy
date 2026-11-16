#version 400 core
#extension GL_ARB_separate_shader_objects : enable

uniform sampler2D u_texture_sampler0;
uniform bool u_override_color;
uniform vec4 u_color;
uniform vec3 u_camera_position;

layout (location = 0) in vec2 v_texture_coord;
layout (location = 1) in vec3 v_normal;
layout (location = 2) in vec3 v_fragment_position;

layout (location = 0) out vec4 o_frag_color;

vec3 calculateDirectionalLight(vec3 normal, vec3 view_direction) {
    vec3 light_direction = vec3(-1.0, 0.0, 1.0);
    vec3 direction = normalize(-light_direction);

    vec3 reflec_direction = reflect(-direction, normal);
    float specular_value = pow(max(dot(view_direction, reflec_direction), 0.0), 1.0);

    return vec3(1.0, 1.0, 1.0) * specular_value;
}

void main() {
    if (u_override_color) {
        o_frag_color = u_color;
        return;
    }

    vec3 normal = normalize(v_normal);
    vec3 view_direction = normalize(u_camera_position - v_fragment_position);

//    vec4 light = vec4(calculateDirectionalLight(normal, view_direction), 1.0);

    o_frag_color = texture(u_texture_sampler0, v_texture_coord) * u_color;
}