#!/usr/bin/perl
# Author: Petr Vileta, 2012
# License: WTFPL - Do What The Fuck You Want To Public License, http://sam.zoy.org/wtfpl/

use strict;
use DBI;
use CGI qw(:standard);
use CGI::Carp qw(fatalsToBrowser);
use CGI::Cookie;
use Digest::MD5 qw(md5_hex);
require 'init.pl';
$|=1;

our ($sth,$dbh,$fileid,$admin,$user,$userid,$hash,$soubor,$ext,$name,$filetype,%kuky,$group,$lead);
our ($db,$dbhost,$dbport,$dbuser,$dbpw)=connect_db();
$fileid=param('file')*1;
$admin=param('req')*1;
$dbh = DBI->connect("DBI:mysql:$db:$dbhost:$dbport",$dbuser,$dbpw) or die "Can't connect: $DBI::errstr\n";
$dbh->do("SET character_set_connection=utf8");
$dbh->do("SET character_set_client=utf8");
$dbh->do("SET character_set_results=utf8");
our $mainpath=get_setup('data_path','string');
$mainpath=~s#\/+$##;
$sth=$dbh->prepare("select `user_id`,`soubor`,`druh`
  		from `evidence_dokumenty` where `id`=?");
$sth->execute($fileid) or die $sth->errstr;
unless($sth->rows)
	{
	send_error("Soubor nebyl nalezen");
	goto SLUS;
	}
$sth->bind_columns(\($userid,$soubor,$filetype));
$sth->fetch;
$ext=$name='';
if($soubor=~m/^(.+)\.(.+)$/)
	{
	$name=lc($1);
	$ext=lc($2);
	}
else
	{
	$name=$soubor;
	}
if($filetype > 1 and $filetype < 5)
	{
	$mainpath .= '/public';
	goto SEND;
	}
if(lc($ENV{REQUEST_METHOD}) eq 'post' and param('user') and param('pass'))
	{
	$user=lecit(param('user'));
	my $pass=lecit(param('pass'));
	my $sth=$dbh->prepare("select `user_id`,`user_password` from `phpbb_users`
			where `username` like ?");
	$sth->execute($user) or die $sth->errstr;
	$sth->bind_columns(\($admin,$hash));
	unless($sth->rows)
		{
		send_error("Uzivatel nebyl nalezen, nebo je chybne heslo");
		goto SLUS;
		}
	$sth->fetch;
	unless(phpbb_check_hash($pass,$hash))
		{
		send_error("Uzivatel nebyl nalezen, nebo je chybne heslo");
		goto SLUS;
		}
	}
else
	{
	$sth=$dbh->prepare("select `username`,`user_password` from `phpbb_users`
			where `user_id` like ?");
	$sth->execute($admin) or die $sth->errstr;
	$sth->bind_columns(\($user,$hash));
	unless($sth->rows)
		{
		send_error("Uzivatel nebyl nalezen, nebo je chybne heslo");
		goto SLUS;
		}
	$sth->fetch;
	%kuky = CGI::Cookie->fetch;
	unless(defined(%kuky->{ao_admin}))
		{
		if(lc($ENV{HTTPS}) ne 'on' and $ENV{HTTP_HOST} ne 'petr1')
			{
			print 'Location: https://',$ENV{HTTP_HOST},'?',$ENV{QUERY_STRING},"&form=1\n\n";
			}
		else
			{
			&loginform;
			}
		goto SLUS;
		}
	unless(check_cookies())
		{
		send_error("Nemate opravneni stahnout tento soubor (cookies?)");
		goto SLUS;
		}
	}
goto SEND if($admin==$userid);
my $aogroup=get_setup('ao_group','number');
# je $admin ve skupine ao_groups ?
$sth=$dbh->prepare("select count(*) from `phpbb_user_group`
		where user_id=? and group_id=?");
$sth->execute($admin,$aogroup) or die $sth->errstr;
my ($ok)=$sth->fetchrow_array;
goto SEND if($ok);
# hledej opravneneho uzivatele
$sth=$dbh->prepare("select FIND_IN_SET(?,`smi_cist`) OR FIND_IN_SET(?,`smi_menit`)
		from `evidence_dokumenty`
		where `id`=?");
my $usr=sprintf("U%01d",$admin);
$sth->execute($usr,$usr,$fileid) or die $sth->errstr;
($ok)=$sth->fetchrow_array;
goto SEND if($ok);

# hledej opravnenou beznou skupinu
my $sth2=$dbh->prepare("select `group_id`,`group_leader`
			from `phpbb_user_group`
			where `user_id`=?");
$sth2->execute($admin) or die $sth2->errstr;
$sth2->bind_columns(\($group,$lead));
while ($sth2->fetch)
	{
	$usr=sprintf("G%01d",$group);
	$sth->execute($usr,$usr,$fileid) or die $sth->errstr;
	($ok)=$sth->fetchrow_array;
	if(!$ok and $lead)
		{
		$usr=sprintf("G%01dL",$group); # hledej leadera skupiny
		$sth->execute($usr,$usr,$fileid) or die $sth->errstr;
		($ok)=$sth->fetchrow_array;
		}
	last if($ok);
	}
$sth2->finish;
unless($ok)
	{
	send_error("Nemate opravneni stahnout tento soubor (Admin=$admin, Userid=$userid)");
	goto SLUS;
	}
SEND:
my $ext2=get_setup('dokumenty_avatar_ext','string');
my $ext3=get_setup('dokumenty_foto_ext','string');
if(1*(",$ext2,")=~m/,$ext,/ or 1*(",$ext3,")=~m/,$ext,/)
	{
	sendit("image/$ext","$name\_$userid.$ext");
	}
else
	{
	sendit("application/$ext","$name\_$userid.$ext");
	}
SLUS:
$sth->finish;
$dbh->disconnect;

sub send_error
{
my $err=shift;
print "Content-Type: text/plain\n",
	"Accept-Ranges: bytes\n",
 	"Cache-Control: no-cache, no-store, no-transform, must-revalidate\n",
	"Content-Length: ",length($err),"\n\n",$err;
}

sub sendit
{
my ($type,$name)=@_;
my $fajl="$mainpath/$userid/$soubor";
my $size=(stat($fajl))[7];
binmode STDOUT;
print "Content-Type: $type\n",
	"Accept-Ranges: bytes\n",
 	"Cache-Control: no-cache, no-store, no-transform, must-revalidate\n",
	"Content-disposition: inline; filename=",($name ? $name : $soubor),"\n",
	"Content-Length: $size\n\n";
open(F,"< $fajl");
binmode F;
while(my $data=<F>)
	{
	print $data;
	}
close F;
}

sub lecit
{
my $lecitprm=shift;
return '' if(length($lecitprm)==0);
$lecitprm=~s/\;\s*(drop|alter|truncate)\s+table\s+//sgi;
$lecitprm=~s/\;\s*drop\s+database\s+//sgi;
$lecitprm=~s/\;\s*delete\s+from\s+//sgi;
$lecitprm=~s/\;\s*insert\s+into\s+//sgi;
$lecitprm=~s/\;\s*(update|replace)\s+//sgi;
return $lecitprm; 
}

sub check_cookies
{
use vars qw/$dbh $user/;
my ($id,$hash,$ses,$sth);
$user=%kuky->{ao_admin}->{value}->[0];
$ses=%kuky->{ao_admin}->{value}->[1];
param('user',$user);
$sth=$dbh->prepare("select `user_id`,`user_password` from `phpbb_users`
		where `username` like ?");
$sth->execute($user) or die $sth->errstr;
$sth->bind_columns(\($id,$hash));
unless($sth->rows)
	{
	$sth->finish;
	return 0;
	}
$sth->fetch;
$sth->finish;
if(md5_hex($hash,$user) eq $ses)
	{
#	$userid=$id;
#	$adminhash=$hash;
	return 1;
	}
$user='';
#$userid=0;
return 0;
}

sub loginform
{
print qq~Cache-Control: no-cache, no-store, no-transform, must-revalidate
Pragma: no-cache
Content-type: text/html

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<meta http-equiv="Content-language" content="cs">
<meta http-equiv="Cache-control" content="no-cache">
<meta name="pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<meta http-equiv="Content-language" content="cs">
<title>Evidence členů</title>
<script type='text/javascript'>
function set_focus()
{
document.getElementById('user').focus();
}
</script>
<link rel="Stylesheet" href="style.css">
</head>
<body onload="set_focus()">
<h1 style='text-align: center'>Stažení souboru</h1>
<form action='filesend.cgi' method='post'>
<input type='hidden' name='file' value='$fileid'>
Přihlášení&nbsp;&nbsp;<b>Jméno:</b>
<input id='user' type='text' name='user'>&nbsp;&nbsp;
<b>Heslo:</b><input type='password' name='pass'>&nbsp;&nbsp;
<input type='submit' name='login' value='Přihlásit se'></form>
</body></html>
~;
}

sub phpbb_check_hash
{
my ($password, $hash)=@_;
my $itoa64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
if(length($hash) == 34)
	{
	return (_hash_crypt_private($password, $hash, $itoa64) eq $hash);
	}
return (md5_hex($password) == $hash);
}

sub _hash_crypt_private
{
my ($password, $setting, $itoa64)=@_;
my $output = '*';
if (substr($setting, 0, 3) != '$H$')
	{
	return $output;
	}
my $count_log2 = index($itoa64,substr($setting,3,1));
if ($count_log2 < 7 || $count_log2 > 30)
	{
	return $output;
	}
my $count = 1 << $count_log2;
my $salt = substr($setting, 4, 8);
if(length($salt) != 8)
	{
	return $output;
	}
my $hash = pack('H*', md5_hex($salt . $password));
while($count)
	{
	$hash = pack('H*', md5_hex($hash . $password));
	$count--;
	}
$output = substr($setting, 0, 12);
$output .= _hash_encode64($hash, 16, $itoa64);
return $output;
}

sub _hash_encode64
{
my ($input, $count, $itoa64)=@_;
my $output = '';
my $i = 0;
while ($i < $count)
	{
	my $value = ord(substr($input,$i,1));
	$i++;
	$output .= substr($itoa64,($value & 0x3f),1);

	if ($i < $count)
		{
		$value |= ord(substr($input,$i,1)) << 8;
		}

	$output .= substr($itoa64,(($value >> 6) & 0x3f),1);

	if ($i++ >= $count)
		{
		last;
		}

	if ($i < $count)
		{
		$value |= ord(substr($input,$i,1)) << 16;
		}

	$output .= substr($itoa64,(($value >> 12) & 0x3f),1);

	if ($i++ >= $count)
		{
		last;
		}

	$output .= substr($itoa64,(($value >> 18) & 0x3f),1);
	}
return $output;
}
