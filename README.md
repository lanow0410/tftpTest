# tftpTest

네트워크프로그래밍 기말과제 프로젝트

UDP기반으로 서버와 통신하여 서버에 존재하는 파일을 기능(get or put)을 선택하여 통신(downlod or upload)하는 기능

타임아웃을 추가하여 블락된 상태로 계속 유지되지 않고 일정이상 통신시도 후에는 종료하는 기능을 추가

사용법

가. pycharm에서의 사용법
1. 우클릭 후 실행 구성 수정으로 진입
2. 스크립트 매개변수 작성
   ㄴ 서버ip주소 기능(get or put) 파일명
ex) 255.255.255.255 get test.txt

나.리눅스환경에서의 사용법
아래의 명령어로 실행
python mytftp.py server_ip get(or put) filename [-p port]

server_ip : TFTP 서버의 IP 주소
get(or put) : 파일을 다운로드(get)하거나 업로드(put)할지 선택
filename : 전송할 파일의 이름
-p port : 서버 포트 번호 (옵션, 기본값 69번)
ㄴ 입력값이 없으면 기본값인 69번 포트로 통신
ex) python mytftp.py 255.255.255.255 get test.txt
