$(document).ready(function() {
	$.get('/pyvmomi-community-samples/templates/navbar.html', function(data) {
		$('#page_wrap').prepend(data);
	});
	$.get('/pyvmomi-community-samples/templates/footer.html', function(data) {
		$('#page_wrap').append(data);
	});
});
