var page = 1;
var page_judge = 0;

// 1表示不在加载
var not_loading = 1;

// 1不是最后一行
var not_last = 1;

// 当前路由
var endpoint = window.location.pathname;

// 绑定滚动事件
$(window).scroll(function getPage(){
    var id;
    var cur_page;

    // 判断滚动条位置
    // clientHeight 视窗的高度，即在浏览器中所能看到的内容的高度
    // scrollTop 视窗上面隐藏掉的部分，即滚动条滚动的距离
    // scrollHeight 真实内容的高度
    var a = document.documentElement.scrollTop == 0 ? document.body.clientHeight : document.documentElement.clientHeight;
    var b = document.documentElement.scrollTop == 0 ? document.body.scrollTop : document.documentElement.scrollTop;
    var c = document.documentElement.scrollTop == 0 ? document.body.scrollHeight : document.documentElement.scrollHeight;

    // b == 0 表示在顶部,没有滑动
    if (b != 0){
        // 到达底端
        if (a + b == c) {
//            alert(not_last)
//            alert(not_loading)
            if (not_loading == 1 && not_last == 1){
                page = page + 1;
//                alert(page)
            }
            loading();

            function loading(){
                if(not_loading==1 && not_last==1){
                   not_loading=0;

                   $.ajax({
                        type: "get",
                        url: endpoint,
                        data: {"page": page},
                        beforeSend: function(){
//                            alert(endpoint)
                            $("#tab_content").append("<div class='spinner'><div class='double-bounce1'></div><div class='double-bounce2'></div></div>");
                        },
                        success: function(data, status){
//                            alert(data)

                            if (data == "" || null){
                                not_last = 0;
                            }
                            $("#tab_content").append(data);
                            not_loading=1;
                        },
                        complete: function(){
                            $(".spinner").remove();
                        },
                        error: function(){
                            console.info("error!")
                        }
                    });
                }

            }

        }
    }
});


var phone;
var fid;
var reply_id;
function feedback_send_message(obj){
    phone = $(obj).attr("data-tel");
    fid = $(obj).attr("data-fid");
    reply_id = $(obj).attr("id");
    $("div.popup_box").show();
    $(".cover_box").show();
}


function popup_cancel(){
    $(".popup_box").hide();
    $(".cover_box").hide();
}


function feedback_answer(){
    if (document.getElementById("popup_textarea").value == ""){
        $.growl.warning({ message: "内容不能为空!"})
    }
    else{
    //    $("#send-button").attr("disabled", "disabled");
        $("#send-button").button("loading");
        var text_data = $(".text_area").val();
        $.post(
            "/fbanswer",
            { "message": $(".text_area").val(),
              "phone": phone
             },
            function(data){
                var new_data = JSON.parse(data);
                $(".popup_box").hide();
                $(".cover_box").hide();
                if(new_data.code == 0){
                    $.growl.notice({message: "发送成功!" });
                    $("#send-button").button("reset");
                    $(".text_area").val('');
//                    $("#send-button").dequeue();
                    $.post(
                        "/fbanswer",
                        { "fid": fid,
                          "if_reply": 1,
                          "reply_content": text_data
                        }
                    );
                    $("#"+reply_id).attr("disabled", "disabled");
                }
                else{
                    $.growl.error({ message: "发送失败!" });
                    $("#send-button").button("reset");
    //                $("#send-button").dequeue();
                }
            }
        );
    }
}


//生成excel
function generate_excel(obj){
//    alert("start")
    $(".generate-excel").button("loading");
    $.post(
        "/totalstatics",
        {"download_args": 1},
        function(data){
            var new_data = JSON.parse(data);
            if(new_data.code == 1){
                $.growl.notice({ message: "生成成功!" });
                $(".generate-excel").button("reset");
//                alert("END")
            }
        }
    );
}