$('.page-register .form-group input').keydown(function() {
  $(this).parent().removeClass('control-error');
  $(this).parent().removeClass('control-success');
})
