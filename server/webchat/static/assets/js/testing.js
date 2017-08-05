$(function() {
  // When we're using HTTPS, use WSS too.
  var ws_host = location.origin.replace(/^http/, 'ws')
  var session_key = $("#sessionkey").val();
  var chatsock = new ReconnectingWebSocket(ws_host + "/chat/" + $("#roomLabel").html() + "/?session_key=" + session_key);
  chatsock.debug = true;

  function scrollToEnd() {
    $('#chat').stop().animate({
      scrollTop: $('#chat')[0].scrollHeight
    }, 800);
  }

  chatsock.onmessage = function(message) {
    var data = JSON.parse(message.data);
    var chat = $("#chat")
    var item = $('<div class="chat-message"></div>')

    item.append(
      $('<span class="quiet"></span>').text(data.nickname)
    )

    item.append("<br>")

    item.append(
      $("<span></span>").text(data.body)
    )

    chat.append(item)
    scrollToEnd();
  };

  chatsock.onclose = function() {
    console.log('chatsock closed');
  };

  $("#chatform").on("submit", function(event) {
    event.preventDefault();
    var nickname = $('#nickname').val();
    if (nickname.length === 0) {
      nickname = "You";
    }

    var message = {
      nickname: nickname, // TODO: user name
      body: $('#message').val(),
    }
    chatsock.send(JSON.stringify(message));
    $("#message").val('').focus();
    return false;
  });

  scrollToEnd();
});
