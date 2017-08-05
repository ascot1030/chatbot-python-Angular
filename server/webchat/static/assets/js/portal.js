/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
(function(document, window, $) {
  'use strict';

  window.AppMessage = App.extend({
    connectToWebSocket: function(label) {
      var self = this;
      var ws_host = location.origin.replace(/^http/, 'ws')
      var session_key = $("#sessionkey").val();
      var sock = new ReconnectingWebSocket(ws_host + "/chat/" + label+ "/" + "?session_key=" + session_key);
      sock.debug = self.debug;

      sock.onmessage = function(message) {
        var data = JSON.parse(message.data);

        // update number of messages in the room
        var $badge = $('[data-label='+ label +'] .media-right .badge');
        $badge.html(parseInt($badge.html()) + 1); // increment by 1

        self.refreshChatContent(label);
      }

      return sock;
    },

    refreshRoomsList: function() {
      var self = this;
      var $roomsListContent = $('.app-message-list .rooms');

      $.get('/rooms/', function(response) {
        $roomsListContent.html(response);
        jdenticon(); // Updates all canvas elements with the data-jdenticon-hash attribute
        self.initRoomList();
      });
    },

    refreshChatContent: function(label) {
      var self = this;
      var $chatsContent = $('.app-message-chats .chats');

      $.get('/rooms/', {label: label}, function(response) {
        $chatsContent.html(response);
        self.scrollChatsToBottom();
      });
    },

    scrollChatsToBottom: function() {
      var $chatsWrap = $(".app-message-chats");

      $chatsWrap.stop().animate({
        scrollTop: $chatsWrap[0].scrollHeight
      }, 800);
    },

    handleResize: function() {
      var self = this;

      $(window).on("resize", function() {
        self.scrollChatsToBottom();
      });
    },

    handleTalking: function() {
      var self = this;
      var $chatsWrap = $(".app-message-chats");
      var $chatsContent = $('.app-message-chats .chats');
      var $textarea = $('.message-input textarea');
      var $textareaWrap = $('.app-message-input');
      var $chatsRoom = $('.app-message-list .list-group-item');

      if (self.isUsePoolOfSockets) {
        if ($chatsRoom.length !== 0) {
          // create list of websockets
          var i = 0;
          $chatsRoom.each(function() {
            if (++i > self.MAX_SOCKETS_IN_POOL) return;
            var label = $(this).data('label');
            self.sockets.push({
              label: label,
              socket: self.connectToWebSocket(label)
            });
          });
          self.currentSocket = self.sockets[0].socket;
        }
      } else {
        var label = $chatsRoom.first().data('label');
        self.currentSocket = self.connectToWebSocket(label);
      }
      // activate first Room
      $chatsRoom.first().addClass('active');

      autosize($('.message-input textarea'));

      $textarea.on('autosize:resized', function() {
        var height = $textareaWrap.outerHeight();
        $chatsWrap.css('height', 'calc(100% - ' + height + 'px)');
        self.scrollChatsToBottom();
      });

      self.initRoomList();

      $(".message-input-btn").on("click", function() {
        var talkContents = $(".message-input>.form-control").val();

        if (talkContents.length > 0) {
          var message = {
            nickname: self.loggedUserName,
            body: talkContents,
          }

          self.currentSocket.send(JSON.stringify(message));

          $(".message-input>.form-control").attr("placeholder", "");
          $(".message-input>.form-control").val("");
        } else {
          $(".message-input>.form-control").attr("placeholder", "type text here...");
        }

        $(".message-input>.form-control").focus();

        self.scrollChatsToBottom();
      });
    },

    getSocketByLabel: function(label) {
      var self = this;
      return $.grep(self.sockets, function(e){ return e.label == label; })[0].socket;
    },

    initRoomList: function() {
      var self = this;
      var $chatsRoom = $('.app-message-list .list-group-item');

        $chatsRoom.on("click", function() {
          $chatsRoom.removeClass('active');
          $(this).addClass('active');
          var label = $(this).data('label');

          if (self.isUsePoolOfSockets) {
            self.currentSocket = self.getSocketByLabel(label);
          } else {
            self.currentSocket.close();
            self.currentSocket = self.connectToWebSocket(label);
          }

          self.refreshChatContent(label);
        });

        // delete the room
        $chatsRoom.on('click', '[data-tag=list-delete]', function(e) {
          var label = $(this).closest('.list-group-item').data('label');
          var name = $(this).closest('.list-group-item').data('name');
          bootbox.dialog({
            message: "Do you want to delete the room <b>" + name + "</b>?",
            buttons: {
              success: {
                label: "Delete",
                className: "btn-danger",
                callback: function() {
                  $.ajax({
                    url: $("#roomsUrl").val(),
                    type: 'DELETE',
                    data: {"label": label},
                    success: function(data) {
                      // destroy socket
                      if (self.isUsePoolOfSockets) {
                        var socket = self.getSocketByLabel(label);
                        socket.close();
                        // delete it from list
                        self.sockets = $.grep(
                          self.sockets,
                          function(item, idx) {return item.label == label},
                          true
                        )
                      } else {
                        self.currentSocket.close();
                      }
                      self.refreshRoomsList();
                    }
                  });
                }
              }
            }
          });
        });
    },

    handleNewRoom: function() {
      var self = this;

      $(".new-room-btn").on("click", function() {
        $.post('/rooms/', function(response) {

          self.refreshRoomsList();

          // add websocket
          self.sockets.push({
            label: response.label,
            socket: self.connectToWebSocket(response.label)
          });
          // and activate it
          self.currentSocket = self.sockets[0].socket;
        });
      });
    },

    run: function(next) {
      this.sockets = [];
      this.currentSocket = {};
      this.loggedUserName = $("#username").val();
      this.debug = true;
      this.isUsePoolOfSockets = false;
      this.MAX_SOCKETS_IN_POOL = 10;

      this.scrollChatsToBottom();
      this.handleResize();
      this.handleTalking();
      this.handleNewRoom();
    }
  });

  $(document).ready(function($) {
    AppMessage.run();
  })
}(document, window, jQuery));
