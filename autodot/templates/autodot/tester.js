
var autodot_testdata = {{ test_data|safe }},
	autodot_js_output = {{ model_name }}_tmpl(autodot_testdata|safe),
	autodot_hash = "{{ hash }}",
	autodot_django_output = $("#{{ model_name }}_test_containingdiv_{{ hash }}").html(),
	autodot_test_name = "{{ model_name }}";
if (_.equals(template_js_output, template_django_output) {
	console.log("Autodot template works: " + autodot_test_name + autodot_hash);
} else {
	console.log("Autodot template doesn't work: " + autodot_test_name + autodot_hash);
}